import asyncio
import os
import random
import time
import curses
import configparser

from itertools import cycle, repeat
from functools import partial

from physics import update_speed


SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258


async def sleep(tics=1):
    for _ in range(tics):
        await asyncio.sleep(0)


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

    while row < rows_number:
        draw_frame(canvas, row, column, garbage_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


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


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas, erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()
    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def read_controls(canvas, game_config):
    """Read keys pressed and returns tuple with controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -int(game_config['DEFAULT']['SPACESHIP_SPEED'])

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = int(game_config['DEFAULT']['SPACESHIP_SPEED'])

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = int(game_config['DEFAULT']['SPACESHIP_SPEED'])

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -int(game_config['DEFAULT']['SPACESHIP_SPEED'])

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def get_frame_size(text):
    """Calculate size of multiline text fragment, return pair — number of rows and colums."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


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

    global coroutines
    coroutines = [blink(
        canvas=canvas,
        row=random.randint(star_min_coordinate_by_y, star_max_coordinate_by_y),
        column=random.randint(star_min_coordinate_by_x, star_max_coordinate_by_x),
        offset_tics=random.randint(0, 20),
        symbol=random.choice(game_config['DEFAULT']['VARIANTS_OF_STARS'])
    ) for star in range(int(game_config['DEFAULT']['COUNTS_OF_STARS']))]

    spaceship_coroutine = animate_spaceship(canvas, spaceship_frames, game_config)
    garbage_coroutine = fill_orbit_with_garbage(
        canvas=canvas,
        garbage_frames=garbage_frames,
        window_width=window_width,
        offset_tics=random.randint(0, 20)
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
            continue
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
