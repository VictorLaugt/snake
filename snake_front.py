import snake_back

import tkinter as tk


TAG_WORLD = 'game'
TAG_OBSTACLE = 'obstacle'
TAG_INSPECT = 'inspect'

class SnakeGameWindow(tk.Tk):
    """Implements a frontend for a snake game. The user can control the snake
    with the arrow keys.
    """
    def __init__(self, snake_world, speed, ui_size_coeff):
        super().__init__()
        # backend interface
        self.world = snake_world
        self.world.reset()

        # graphical characteristics
        self.speed = speed
        self.square_side_size = ui_size_coeff

        # pause system
        self.game_paused = False
        self.next_step = None

        # widget declarations
        self.score_text = tk.StringVar(self, self.world.score)
        self.world_grid = tk.Canvas(self,
                                    width=self.world.world_width * self.square_side_size,
                                    height=self.world.world_height * self.square_side_size,
                                    bg='gray')
        self.snake_square_ids = [None] * (self.world.world_width * self.world.world_height)
        self.score_displayer = tk.Entry(self, textvariable=self.score_text)

        # events
        self.bind_all('<space>', lambda _: self.pause())
        self.bind_all('<Escape>', lambda _: self.destroy())
        self.bind_all('<KeyPress-q>', lambda _: self.destroy())
        self.bind_all('<Button-1>', lambda event: self.obstacle_input(event.x, event.y))
        self.bind_snake_control()

        # widget positions
        tk.Label(self, text='Score: ').grid(row=0, column=0, columnspan=1)
        self.score_displayer.grid(row=0, column=1, columnspan=2)
        self.world_grid.grid(row=1, column=0, columnspan=3)

        self.next_step = self.after_idle(self.game_step)

    def bind_snake_control(self):
        self.world_grid.bind_all('<Up>', lambda _: self.direction_input(snake_back.UP))
        self.world_grid.bind_all('<Down>', lambda _: self.direction_input(snake_back.DOWN))
        self.world_grid.bind_all('<Left>', lambda _: self.direction_input(snake_back.LEFT))
        self.world_grid.bind_all('<Right>', lambda _: self.direction_input(snake_back.RIGHT))


    # ---- draw functions
    def square_to_coordinates(self, square):
        """Returns the coordinates of a square on the graphical ui canvas."""
        return square[0] * self.square_side_size, square[1] * self.square_side_size

    def coordinates_to_square(self, x, y):
        """Returns the square of the snake world which corresponds to the `(x, y)`
        coordinates on the graphical ui canvas.
        """
        return int(x / self.square_side_size), int(y / self.square_side_size)

    def draw_square(self, x, y, color, tag):
        shift = self.square_side_size
        return self.world_grid.create_rectangle(x, y, x + shift, y + shift, fill=color, tag=tag)

    def _draw_world(self, head_color, tail_color, food_color):
        self.world_grid.delete(TAG_WORLD)

        # draws the snake
        head, *tail = self.world.snake
        head_x, head_y = self.square_to_coordinates(head)
        self.snake_square_ids[0] = self.draw_square(head_x, head_y, head_color, TAG_WORLD)
        for i, square in enumerate(tail, start=1):
            x, y = self.square_to_coordinates(square)
            self.snake_square_ids[i] = self.draw_square(x, y, tail_color, TAG_WORLD)

        # draws the food
        for food in self.world.food_locations:
            x, y = self.square_to_coordinates(food)
            self.draw_square(x, y, food_color, TAG_WORLD)

    def _draw_obstacles(self, obstacle_color):
        self.world_grid.delete(TAG_OBSTACLE)

        # draws the obstacles
        for obstacle in self.world.obstacle_locations:
            x, y = self.square_to_coordinates(obstacle)
            self.draw_square(x, y, obstacle_color, TAG_WORLD)

    def draw(self):
        """Draws the entire game."""
        self._draw_world('dark green', 'green', 'red')
        self._draw_obstacles('black')

    def _refresh_score(self):
        """Displays the current score."""
        self.score_text.set(self.world.score)

    def _schedule_death_animation(self):
        """Displays the death animation of the snake."""
        def colorize_red_function(square_id):
            return lambda: self.world_grid.itemconfig(square_id, fill='dark red')
        self.world_grid.itemconfig(self.snake_square_ids[0], fill='dark red')
        for i in range(1, len(self.world.snake)):
            self.after(i * self.speed, colorize_red_function(self.snake_square_ids[i]))


    # ---- gameloop managers
    def _move(self):
        """Moves the snake and returns False if the snake hits something,
        True otherwise.
        """
        continue_game = self.world.move_snake()
        self.draw()
        return continue_game

    def end_game(self):
        """Ends the current game."""
        self._schedule_death_animation()
        self.next_step = self.after(self.speed * (len(self.world.snake)+1), self.game_step)
        self.world.reset()

    def game_step(self):
        """Executes one step of the game loop."""
        self._refresh_score()
        if self._move():
            # the game continues
            self.next_step = self.after(self.speed, self.game_step)
        else:
            # the game is over
            self.end_game()

    def pause(self):
        """Pauses or resumes the game."""
        self.game_paused = not self.game_paused
        if self.game_paused:
            self.score_text.set('Game paused')
            self.after_cancel(self.next_step)
            self.next_step = None
        else:
            self.next_step = self.after_idle(self.game_step)


    # ---- events
    def direction_input(self, direction):
        """Calls the backend to add a new requested direction."""
        if direction is not None:
            self.world.add_request(direction)

    def obstacle_input(self, x, y):
        """Calls the backend to add or remove an obstacle."""
        square = self.coordinates_to_square(x, y)
        if square in self.world.obstacle_locations:
            self.world.discard_obstacle(square)
        elif square not in self.world.snake and square not in self.world.food_locations:
            self.world.add_obstacle(square)
        self._draw_obstacles('black')


class AutomaticSnakeGameWindow(SnakeGameWindow):
    """Implements a frontend for a snake game. An algorithm is used to control
    the snake, the user cannot interfere with it.
    """
    def __init__(self, snake_world, speed, ui_size_coeff, ai):
        super().__init__(snake_world, speed, ui_size_coeff)
        self.ai = ai

    def bind_snake_control(self):
        pass # only the ai is allowed to control the snake.


    # ---- draw functions
    def _draw_ai_inspection(self, color):
        self.world_grid.delete(TAG_INSPECT)

        for i, square in enumerate(self.ai.inspect()):
            x, y = self.square_to_coordinates(square)
            self.draw_square(x, y, color, TAG_INSPECT)

    def draw(self):
        self._draw_ai_inspection('yellow')
        super().draw()


    # ---- gameloop managers
    def game_step(self):
        self.direction_input(self.ai.get_input())
        super().game_step()

    def end_game(self):
        super().end_game()
        self.ai.reset()
        # self.pause()
