#Pydroid should import tkinter
from itertools import chain

from front import SnakeGameWindow, MobileSnakeGameWindow
from agent import PlayerSnakeAgent, AStarSnakeAgent, AStarOffensiveSnakeAgent
from world import SnakeWorld, EuclidianDistanceHeuristic, ManhattanDistanceHeuristic


def build_world(height: int, width: int, n_food: int) -> SnakeWorld:
    dx = int(0.2 * width)
    dy = 1
    init_length = int(0.36 * height)

    x_left = dx
    x_right = width - dx - 1
    
    attack_anticipation = int(0.3*(height + width))

    world = SnakeWorld(width, height, n_food)

    blue = PlayerSnakeAgent(
        world,
        initial_pos=[(x_left, y) for y in range(init_length-1+dy, -1+dy, -1)],
        initial_dir=(0, 1)
    )

    yellow = AStarOffensiveSnakeAgent(
        world,
        initial_pos=[(x_right, y) for y in range(init_length-1+dy, -1+dy, -1)],
        initial_dir=(0, 1),
        heuristic_type=EuclidianDistanceHeuristic,
        latency=0,
        caution=1,
        attack_anticipation=attack_anticipation
    )

    purple = AStarOffensiveSnakeAgent(
        world,
        initial_pos=[(x_left, y) for y in range(height-1-dy, height-1-init_length-dy, -1)],
        initial_dir=(0, 1),
        heuristic_type=EuclidianDistanceHeuristic,
        latency=0,
        # caution=2,
        caution=1,
        attack_anticipation=attack_anticipation
    )

    green = AStarOffensiveSnakeAgent(
        world,
        initial_pos=[(x_right, y) for y in range(height-init_length-dy, height-dy, 1)],
        initial_dir=(0, -1),
        heuristic_type=EuclidianDistanceHeuristic,
        latency=0,
        # caution=3,
        caution=3,
        attack_anticipation=attack_anticipation
    )

    #yellow.add_opponent(green)
    yellow.add_opponent(blue)
    purple.add_opponent(blue)
    green.add_opponent(blue)

    player_agents = [blue]
    ai_agents = [yellow, purple, green]

    for agent in chain(player_agents, ai_agents):
        world.attach_agent(agent)

    return world, player_agents, ai_agents


# height, width = 25, 25
height, width = 20, 20
world, player_agents, ai_agents = build_world(height, width, n_food=2)

gui = MobileSnakeGameWindow(
    world,
    player_agents=player_agents,
    ai_agents=ai_agents,
    explain_ai=False,
    ui_size_coeff=1000/max(height, width),
    # time_step=100
    time_step=150
    # time_step=200
    # time_step=250
)
gui.mainloop()
