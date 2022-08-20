import time
import curses
import asyncio
import random
from itertools import cycle, repeat
import configparser

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258

GAME_CONFIG = configparser.ConfigParser()
GAME_CONFIG.read('config.ini')
VARIANTS_OF_STARS = GAME_CONFIG['DEFAULT']['VARIANTS_OF_STARS']
COUNTS_OF_STARS = int(GAME_CONFIG['DEFAULT']['COUNTS_OF_STARS'])
SPACESHIP_SPEED = int(GAME_CONFIG['DEFAULT']['SPACESHIP_SPEED'])


async def blink(canvas, row, column, symbol='*'):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for await_number in range(random.randint(0, 20)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for await_number in range(random.randint(0, 3)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for await_number in range(random.randint(0, 5)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for await_number in range(random.randint(0, 3)):
            await asyncio.sleep(0)


async def animate_spaceship(canvas, frames_of_spaceship):

    window = curses.initscr()
    # Метод getmaxyx возвращает кортеж высоты и ширины окна
    # Подробнее в документации:
    # https://docs.python.org/3/library/curses.html#curses.window.getmaxyx
    window_height, window_width = window.getmaxyx()
    first_frame_of_spaceship = frames_of_spaceship[0]
    second_frame_of_spaceship = frames_of_spaceship[1]

    first_animation_frames = list(repeat(first_frame_of_spaceship, 2))
    second_animation_frames = list(repeat(second_frame_of_spaceship, 2))
    frames_for_animation_spaceship = first_animation_frames + \
                                     second_animation_frames

    frame_size = get_frame_size(first_frame_of_spaceship)
    frame_height, frame_width = frame_size
    border_size = 1

    # Стартовые позиции - изначально это центр игрового поля
    row_position = window_height // 2 - frame_height // 2
    column_position = window_width // 2 - frame_width // 2
    previous_frame = ''

    for spaceship_frame in cycle(frames_for_animation_spaceship):
        coordinates = read_controls(canvas)
        row_direction, column_direction, space_pressed = coordinates
        draw_frame(canvas, row_position, column_position, previous_frame,
                   negative=True)

        row_position += row_direction
        column_position += column_direction

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

        draw_frame(canvas, row_position, column_position, spaceship_frame)
        previous_frame = spaceship_frame

        await asyncio.sleep(0)


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


def read_controls(canvas):
    """Read keys pressed and returns tuple with controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -SPACESHIP_SPEED

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = SPACESHIP_SPEED

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = SPACESHIP_SPEED

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -SPACESHIP_SPEED

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def get_frame_size(text):
    """Calculate size of multiline text fragment, return pair — number of rows and colums."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def draw(canvas, frames):
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

    coroutines = [blink(
        canvas,
        random.randint(star_min_coordinate_by_y, star_max_coordinate_by_y),
        random.randint(star_min_coordinate_by_x, star_max_coordinate_by_x),
        random.choice(VARIANTS_OF_STARS)
    ) for star in range(COUNTS_OF_STARS)]

    spaceship_coroutine = animate_spaceship(canvas, frames)
    coroutines.append(spaceship_coroutine)

    while True:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()
        time.sleep(0.1)


def main():
    spaceship_frames = []

    for frame in range(1, 3):
        with open(f'frames/rocket_frame_{frame}.txt', 'r') as rocket_frame:
            spaceship_frame = rocket_frame.readlines()
        spaceship_frames.append(''.join(spaceship_frame))

    curses.update_lines_cols()
    curses.wrapper(draw, spaceship_frames)


if __name__ == '__main__':
    main()
