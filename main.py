import asyncio
import os
import random
import time
import curses
import configparser

from itertools import cycle, repeat
from functools import partial

from physics import update_speed
from curses_tools import draw_frame, read_controls, get_frame_size
from obstacles import Obstacle
from exlposion import explode


obstacles = []
coroutines = []
obstacles_in_last_collisions = []


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


async def show_gameover(canvas, center_row, center_column):
    with open("frames/game_over.txt", 'r') as file:
        game_over_frame = file.read()

    rows, columns = get_frame_size(game_over_frame)
    corner_row = center_row - rows / 2
    corner_column = center_column - columns / 2

    while True:
        draw_frame(canvas, corner_row, corner_column, game_over_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, corner_row, corner_column, game_over_frame,
                   negative=True)


async def fire(canvas, start_row, start_column, rows_speed=-0.6, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        collisions = [obstacles_in_last_collisions.append(obstacle) for
                      obstacle in obstacles
                      if obstacle.has_collision(row, column)]
        if collisions:
            return

        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def blink(canvas, row, column, offset_tics, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(offset_tics)

        canvas.addstr(row, column, symbol)
        await sleep(3)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0
    frame_height, frame_width = get_frame_size(garbage_frame)
    obstacle = Obstacle(row, column, frame_height, frame_width)
    obstacles.append(obstacle)

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        obstacle.row, obstacle.column = row, column
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed

        if obstacle in obstacles_in_last_collisions:
            obstacles_in_last_collisions.remove(obstacle)
            await explode(canvas, row + 5, column + 5)
            break

    obstacles.remove(obstacle)


async def animate_spaceship(canvas, frames_of_spaceship, game_config):
    window = curses.initscr()
    # Метод getmaxyx возвращает кортеж высоты и ширины окна
    # Подробнее в документации:
    # https://docs.python.org/3/library/curses.html#curses.window.getmaxyx
    window_height, window_width = window.getmaxyx()
    first_frame_of_spaceship, second_frame_of_spaceship = frames_of_spaceship

    first_step_animation = list(repeat(first_frame_of_spaceship, 2))
    second_step_animation = list(repeat(second_frame_of_spaceship, 2))
    spaceship_animation = first_step_animation + second_step_animation

    frame_size = get_frame_size(first_frame_of_spaceship)
    frame_height, frame_width = frame_size
    border_size = 1

    # Стартовые позиции - изначально это центр игрового поля
    row_position = window_height // 2 - frame_height // 2
    column_position = window_width // 2 - frame_width // 2
    row_speed = column_speed = 0

    for spaceship_frame in cycle(spaceship_animation):
        coordinates = read_controls(canvas, game_config)
        row_direction, column_direction, space_pressed = coordinates
        if space_pressed:
            coroutines.append(fire(
                canvas=canvas,
                start_column=column_position + 2,
                start_row=row_position
            ))
        row_speed, column_speed = update_speed(
            row_speed, column_speed, coordinates[0], coordinates[1]
        )

        row_position += row_speed
        column_position += column_speed

        row_position = min(
            window_height - frame_height - border_size,
            row_position
        )
        column_position = min(
            window_width - frame_width - border_size,
            column_position
        )
        row_position = max(1, row_position)
        column_position = max(1, column_position)

        collision_with_spaceship = [
            obstacle for obstacle in obstacles
            if obstacle.has_collision(
                row_position, column_position, frame_size[0], frame_size[1]
            )
        ]
        if collision_with_spaceship:
            center_row, center_column = window_height // 2, window_width // 2
            await show_gameover(canvas, center_row, center_column)

        previous_frame = spaceship_frame
        draw_frame(canvas, row_position, column_position, previous_frame)

        await asyncio.sleep(0)
        draw_frame(canvas, row_position, column_position, spaceship_frame,
                   negative=True)


async def fill_orbit_with_garbage(canvas, offset_tics, garbage_frames, window_width):
    garbage_frame_size = 10
    while True:
        frame = random.choice(garbage_frames)
        trash_coroutine = fly_garbage(
                    canvas,
                    garbage_frame=frame,
                    column=random.randint(garbage_frame_size, window_width -
                                          garbage_frame_size))
        coroutines.append(trash_coroutine)

        await sleep(offset_tics)



def draw(canvas, spaceship_frames, garbage_frames, game_config):
    canvas.border()
    window = curses.initscr()
    # Метод getmaxyx возвращает кортеж высоты и ширины окна
    # Подробнее в документации:
    # https://docs.python.org/3/library/curses.html#curses.window.getmaxyx
    window_height, window_width = window.getmaxyx()
    border_size = 2
    # Вычисление самых ближних точек координат к границе игрового поля для звезд
    star_max_coordinate_by_x = window_width - border_size
    star_min_coordinate_by_x = 1
    star_max_coordinate_by_y = window_height - border_size
    star_min_coordinate_by_y = 1
    window.nodelay(True)
    curses.curs_set(False)

    coroutines.extend([blink(
        canvas=canvas,
        row=random.randint(star_min_coordinate_by_y, star_max_coordinate_by_y),
        column=random.randint(star_min_coordinate_by_x, star_max_coordinate_by_x),
        offset_tics=random.randint(0, 20),
        symbol=random.choice(game_config['DEFAULT']['VARIANTS_OF_STARS'])
    ) for star in range(int(game_config['DEFAULT']['COUNTS_OF_STARS']))])

    spaceship_coroutine = animate_spaceship(canvas, spaceship_frames, game_config)
    garbage_coroutine = fill_orbit_with_garbage(
        canvas=canvas,
        garbage_frames=garbage_frames,
        window_width=window_width,
        offset_tics=random.randint(4, 20)
    )

    coroutines.append(spaceship_coroutine)
    coroutines.append(garbage_coroutine)

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(0.1)


def main():
    game_config = configparser.ConfigParser()
    game_config.read('config.ini')
    spaceship_frames = []
    garbage_frames = []

    for frame_file in os.listdir("frames"):
        with open(f"frames/{frame_file}", 'r') as frame:
            frame = frame.readlines()

        if frame_file.startswith("rocket"):
            spaceship_frames.append(''.join(frame))

        if frame_file.startswith("trash"):
            garbage_frames.append(''.join(frame))

    curses.update_lines_cols()
    curses.wrapper(
        partial(
            draw,
            game_config=game_config,
            spaceship_frames=spaceship_frames,
            garbage_frames=garbage_frames
        )
    )


if __name__ == '__main__':
    main()
