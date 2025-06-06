from __future__ import annotations

from abc import ABC, abstractmethod
from random import randrange
import numpy as np
from collections import deque

from direction import UP, DOWN, LEFT, RIGHT, toward_center
from voronoi import furthest_voronoi_vertex

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Iterator, Sequence, Optional
    from type_hints import Position, Direction
    from agent import AbstractSnakeAgent


class AbstractGridGraph(ABC):
    @abstractmethod
    def get_width(self) -> int:
        pass

    @abstractmethod
    def get_height(self) -> int:
        pass

    @abstractmethod
    def get_neighbor(self, p: Position, d: Direction) -> Position:
        """Returns the neighbor of position `p` in the direction `d`."""

    @abstractmethod
    def iter_free_neighbors(self) -> Iterator[tuple[Position, Direction]]:
        """Iterates over each neighbor of position `p` which does not contains
        any obstacle.
        """


class AbstractHeuristic(ABC):
    @abstractmethod
    def __init__(self, graph: AbstractGridGraph, x_dst: int, y_dst: int) -> None:
        pass

    @abstractmethod
    def __call__(self, x: int, y: int) -> int:
        pass


class EuclidianDistanceHeuristic(AbstractHeuristic):
    def __init__(self, graph: AbstractGridGraph, x_dst: int, y_dst: int) -> None:
        self.x_dst = x_dst
        self.y_dst = y_dst

    def __call__(self, x: int, y: int) -> int:
        dx, dy = self.x_dst - x, self.y_dst - y
        return dx*dx + dy*dy

class ManhattanDistanceHeuristic(AbstractHeuristic):
    def __init__(self, graph: AbstractGridGraph, x_dst: int, y_dst: int) -> None:
        self.x_dst = x_dst
        self.y_dst = y_dst

    def __call__(self, x: int, y: int) -> int:
        return abs(self.x_dst - x) + abs(self.y_dst - y)

class EuclidianDistancePeriodicHeuristic(AbstractHeuristic):
    def __init__(self, graph: AbstractGridGraph, x_dst: int, y_dst: int) -> None:
        self.h = graph.get_height()
        self.w = graph.get_width()
        self.x_dst = x_dst
        self.y_dst = y_dst

    def __call__(self, x: int, y: int) -> int:
        dx, dy = abs(self.x_dst - x), abs(self.y_dst - y)
        dx, dy = min(dx, self.w - dx), min(dy, self.h - dy)
        return dx*dx + dy*dy


class SnakeWorld(AbstractGridGraph):
    def __init__(
        self,
        width: int,
        height: int,
        n_food: int,
        respawn_cooldown: Optional[int]=None
    ) -> None:
        assert width > 0 and height > 0
        assert n_food >= 0
        assert respawn_cooldown is None or respawn_cooldown >= 0

        self.width = width
        self.height = height
        self.initial_n_food = n_food
        if respawn_cooldown is None:
            self.initial_respawn_cooldown = float('+inf')
        else:
            self.initial_respawn_cooldown = respawn_cooldown

        self.obstacle_count = np.zeros((self.width, self.height), dtype=np.uint8)
        self.food_pos: set[Position] = set()
        self.respawn_cooldown = self.initial_respawn_cooldown
        self.alive_agents: list[AbstractSnakeAgent] = []
        self.dead_agents: deque[AbstractSnakeAgent] = deque()

    def __repr__(self) -> str:
        repr_grid = [['  .  '  for x in range(self.width)] for y in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                repr_grid[y][x] = f" {self.obstacle_count[x, y]:03d} "
                if (x, y) in self.food_pos:
                    repr_grid[y][x] = "  *  "
        return '\n'.join(''.join(row) for row in repr_grid) + '\n'

    # ---- private
    def _consume_food(self, p: Position) -> bool:
        """If a food and only one snake head is at position `p`, despawn this food
        and returns True. Else, returns False.
        """
        if p in self.food_pos:
            head_count = sum((agent.get_head() == p) for agent in self.alive_agents)
            if head_count == 1:
                self.food_pos.remove(p)
                return True
        return False

    def _find_available_food_pos(self, max_try: int=20) -> Optional[Position]:
        """Tries to find an available position to spawn a new food and returns
        it if found.
        """
        for _ in range(max_try):
            pos = (randrange(self.width), randrange(self.height))
            if self.obstacle_count[pos] == 0 and pos not in self.food_pos:
                return pos

    def _spawn_missing_food(self) -> None:
        # q, r = divmod(len(self.alive_agents), 2)
        # n_food = q + (r != 0)
        # for _ in range(n_food - len(self.food_pos)):
        for _ in range(self.initial_n_food - len(self.food_pos)):
            pos = self._find_available_food_pos()
            if pos is None:
                break
            self.food_pos.add(pos)


    def _kill_agents(self, deads: Sequence[AbstractSnakeAgent]) -> None:
        for agent in deads:
            self.alive_agents.remove(agent)
            self.dead_agents.append(agent)

    def _find_agent_spawn_pos(self) -> Optional[Position]:
        """Tries to find a position to spawn an agent and returns it if found."""
        repellent_pos = []
        for agent in self.alive_agents:
            repellent_pos.extend(agent.iter_cells())
        (x, y), _ = furthest_voronoi_vertex(np.array(repellent_pos), self.width, self.height)

        spawn_pos = (int(x), int(y))
        if self.obstacle_count[spawn_pos] == 0:
            return spawn_pos

    def _respawn_dead_agent(self) -> None:
        if len(self.dead_agents) == 0:
            return

        if self.respawn_cooldown > 0:
            self.respawn_cooldown -= 1
            return

        spawn_pos = self._find_agent_spawn_pos()
        if spawn_pos is None:
            return

        agent = self.dead_agents.popleft()
        spawn_length = agent.get_initial_length()
        spawn_dir = toward_center(*spawn_pos, self.width, self.height)

        agent.reset([spawn_pos] * spawn_length, spawn_dir)
        self.alive_agents.append(agent)
        self.obstacle_count[spawn_pos] += spawn_length
        self.respawn_cooldown += self.initial_respawn_cooldown


    # ---- public
    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height


    def pop_obstacle(self, p: Position) -> None:
        """Removes an obstacle from the position `p`."""
        assert self.obstacle_count[p] > 0
        self.obstacle_count[p] -= 1

    def add_obstacle(self, p: Position) -> None:
        """Puts an obstacle on the position `p`."""
        self.obstacle_count[p] += 1

    def pos_is_free(self, p: Position) -> bool:
        """Returns True if there is no obstacle on the position `p`, False otherwise."""
        return self.obstacle_count[p] == 0


    def get_neighbor(self, p: Position, d: Direction) -> Position:
        return (p[0] + d[0]) % self.width, (p[1] + d[1]) % self.height

    def iter_free_neighbors(self, p: Position) -> Iterator[tuple[Position, Direction]]:
        x, y = p
        up_neighbor = (x, (y-1) % self.height)
        down_neighbor = (x, (y+1) % self.height)
        left_neighbor = ((x-1) % self.width, y)
        right_neighbor = ((x+1) % self.width, y)

        if self.obstacle_count[up_neighbor] == 0:
            yield up_neighbor, UP
        if self.obstacle_count[down_neighbor] == 0:
            yield down_neighbor, DOWN
        if self.obstacle_count[left_neighbor] == 0:
            yield left_neighbor, LEFT
        if self.obstacle_count[right_neighbor] == 0:
            yield right_neighbor, RIGHT


    def iter_food(self) -> Iterator[Position]:
        """Iterates over each food position of the world."""
        return iter(self.food_pos)


    def attach_agent(self, agent: AbstractSnakeAgent, alive: bool=True) -> None:
        """Adds a new agent in the world."""
        agent.set_id(len(self.alive_agents) + len(self.dead_agents))
        if alive:
            self.alive_agents.append(agent)
        else:
            self.dead_agents.append(agent)

    def iter_alive_agents(self) -> Iterator[AbstractSnakeAgent]:
        """Returns the agents of the world which are still alive."""
        return iter(self.alive_agents)


    def reset(self) -> None:
        """Reset the world and all its agents to make them ready to start a new game."""
        self.obstacle_count.fill(0)

        self.food_pos.clear()
        self._spawn_missing_food()

        self.respawn_cooldown = self.initial_respawn_cooldown
        self.alive_agents.extend(self.dead_agents)
        self.dead_agents.clear()
        for agent in self.alive_agents:
            agent.reset()
            for pos in agent.iter_cells():
                self.obstacle_count[pos] += 1

    def simulate(self) -> list[AbstractSnakeAgent]:
        """Simulates one step of the world evolution and returns the agents
        which died during this simulation step.
        """
        # moves the snakes
        directions: list[Direction] = []
        for agent in self.alive_agents:
            agent.decide_direction()
            directions.append(agent.get_direction())
        for agent, d in zip(self.alive_agents, directions):
            agent.move(d)

        # resolves the snakes which eat their own tail
        cut_lengths: list[int] = []
        for agent in self.alive_agents:
            cut_lengths.append(agent.check_self_collision())
        for agent, cut_len in zip(self.alive_agents, cut_lengths):
            agent.cut(cut_len)

        # resolves the snakes which eat food and grow
        growing: list[AbstractSnakeAgent] = []
        for agent in self.alive_agents:
            if self._consume_food(agent.get_head()):
                growing.append(agent)
        for agent in growing:
            agent.grow()

        # kills each snake which collides another snake
        deads: list[AbstractSnakeAgent] = []
        for agent in self.alive_agents:
            if agent.collides_another():
                agent.die()
                deads.append(agent)
        self._kill_agents(deads)

        # respawns the foods which has been eaten
        self._spawn_missing_food()

        # respawns dead snakes
        self._respawn_dead_agent()


        return deads
