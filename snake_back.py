from __future__ import annotations

from collections import deque
from random import randrange
from abc import ABC, abstractmethod

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import TypeAlias
    Direction: TypeAlias = tuple[int, int]
    Position: TypeAlias = tuple[int, int]


# directions
UP: Direction =    (0,  -1)
DOWN: Direction =  (0,  1)
LEFT: Direction =  (-1, 0)
RIGHT: Direction = (1,  0)


def oposite(direction: Direction) -> Direction:
    return (-direction[0], -direction[1])


class AbstractSnakeWorld(ABC):
    """Abstract class for a snake game backend.

    Public attributes
    ---------------------------------------------------------------------------
    snake: list[tuple[int, int]]
        Positions of the snake squares. ``snake[0]`` is the snake's head and
        ``snake[1:]`` is the snake's tail.

    food_locations: list[tuple[int, int]]
        Positions of the foods.

    direction: tuple[int, int]
        Direction in which the snake is currently moving.

    score: int
        Current score
    """
    def __init__(
        self,
        food_number: int,
        initial_snake: list[Position],
        initial_dir: Direction
    ) -> None:
        # game constants
        self.initial_direction = initial_dir
        self.initial_snake_position = initial_snake
        self.food_number = food_number

        # game variables
        self.snake: list[Position] = []
        self.food_locations: list[Position] = []
        self.requests: deque[Direction] = deque((), maxlen=5)
        self.direction = None
        self.score = 0

    # ---- public methods
    def reset(self) -> None:
        """Resets the game variables."""
        self.snake.clear()
        self.snake.extend(self.initial_snake_position)

        self.food_locations.clear()
        for _ in range(self.food_number):
            self.food_locations.append(self.get_new_food_position())

        self.direction = self.initial_direction
        self.requests.clear()

        self.score = len(self.snake)

    def add_request(self, requested_direction: Direction) -> None:
        """Adds a new requested direction in which to move the snake."""
        if len(self.requests) < self.requests.maxlen:
            if len(self.requests) > 0:
                last_direction = self.requests[-1]
            else:
                last_direction = self.direction
            if requested_direction != oposite(last_direction):
                self.requests.append(requested_direction)

    def move_snake(self) -> bool:
        """Moves the snake in the next requested direction.
        If the snake eats a food, makes it graw and spawns a new food.
        Returns False if the snake hits an obstacle or its tail, True otherwise.
        """
        # determines the current direction
        if self.requests:
            self.direction = self.requests.popleft()

        # computes the head next position and detects a possible collision with
        # a wall
        head = self.moved_square(self.snake[0], self.direction)
        if self.obstacle_hit(head):
            return False

        # moves the snake tail and detects a possible collision between its head
        # and its tail
        tail_end = self.snake[-1]
        for i in range(len(self.snake)-1, 0, -1):
            tail_square = self.snake[i-1]
            self.snake[i] = tail_square
            if head == tail_square:
                return False
        self.snake[0] = head

        # makes the snake grow if it eats
        for i, food in enumerate(self.food_locations):
            if head == food:
                self.snake.append(tail_end)
                self.score += 1
                self.food_locations[i] = self.get_new_food_position()
                break

        return True

    @abstractmethod
    def add_obstacle(self, square: Position) -> None:
        """Put an obstacle in the world at the position `square`."""

    @abstractmethod
    def discard_obstacle(self, square: Position) -> None:
        """If the position `square` contains an obstacle, remove this obstacle."""

    @abstractmethod
    def win(self) -> bool:
        """Returns True if the game is won, False otherwise."""

    # ---- protected methods
    @abstractmethod
    def get_new_food_position(self) -> Position:
        """Returns the position of a new food."""

    @abstractmethod
    def moved_square(self, square: Position, direction: Direction) -> Position:
        """Returns the position of `square` moved in `direction`."""

    @abstractmethod
    def obstacle_hit(self, square: Position) -> bool:
        """Returns True if `square` touches an obstacle (other than the snake's
        tail), False otherwise.
        """


class SnakeWorld(AbstractSnakeWorld):
    """Implements a snake game backend.

    Public attributes
    ---------------------------------------------------------------------------
    see AbstractSnakeWorld public attributes

    world_width: int
        width of the snake world

    world_height: int
        height of the snake world
    """
    def __init__(
        self,
        world_width: int,
        world_height: int,
        food_number: int,
        initial_snake: list[Position],
        initial_dir: Direction
    ) -> None:
        super().__init__(food_number, initial_snake, initial_dir)
        self.world_width = world_width   # x-axis length
        self.world_height = world_height # y-axis length
        self.world_size = world_width * world_height
        self.obstacle_locations: set[Position] = set()

    def __repr__(self) -> str:
        array = [[None]*self.world_width for y in range(self.world_height)]
        for x in range(self.world_width):
            for y in range(self.world_height):
                square = (x, y)
                if square == self.snake[0]:
                    square_repr = '@'
                elif square in self.snake:
                    square_repr = 'O'
                elif square in self.food_locations:
                    square_repr = '*'
                elif square in self.obstacle_locations:
                    square_repr = 'X'
                else:
                    square_repr = '.'
                array[y][x] = square_repr
        return '\n'.join(''.join(row) for row in array)

    # ---- public methods
    def reset(self) -> None:
        super().reset()
        self.obstacle_locations.clear()

    def add_obstacle(self, square: Position) -> None:
        self.obstacle_locations.add(square)

    def discard_obstacle(self, square) -> None:
        self.obstacle_locations.discard(square)

    def win(self) -> bool:
        return self.count_free_squares() <= 0

    # ---- protected methods
    def count_free_squares(self) -> int:
        return self.world_size - len(self.food_locations) - len(self.snake) - len(self.obstacle_locations)

    def get_new_food_position(self) -> Position:
        assert self.count_free_squares() > 0
        while True:
            new_food = (randrange(self.world_width), randrange(self.world_height))
            if (new_food not in self.snake and
                new_food not in self.food_locations and
                new_food not in self.obstacle_locations
            ):
                return new_food

    def moved_square(self, square: Position, direction: Direction) -> Position:
        return (square[0] + direction[0], square[1] + direction[1])

    def border_hit(self, square: Position) -> bool:
        return not (0 <= square[0] < self.world_width and
                    0 <= square[1] <= self.world_height)

    def obstacle_hit(self, square: Position) -> bool:
        return square in self.obstacle_locations or self.border_hit(square)


class PeriodicSnakeWorld(SnakeWorld):
    """Implements snake game backend in a periodic world.

    Public attributes
    ---------------------------------------------------------------------------
    see SnakeWorld public attributes
    """

    # ---- protected methods
    def moved_square(self, square: Position, direction: Direction) -> Position:
        return (
            (square[0] + direction[0]) % self.world_width,
            (square[1] + direction[1]) % self.world_height
        )

    def border_hit(self, square: Position) -> bool:
        return False
