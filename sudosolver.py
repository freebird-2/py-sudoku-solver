"""
Start reading at solver.run. Simple GUI interface for solving Sudoku puzzles. Updating the GUI is done
automatically with tk.IntVar objects.
"""
import logging
import math
import random
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from typing import Any, Callable

logging.basicConfig(level=logging.DEBUG, format='%(funcName)s (%(lineno)d) :\n%(message)s\n')

RawGrid = list[list[int]]
Group = list[tk.IntVar]
Grid = list[Group]
Coords = tuple[int, int]
StateChangeHandler = Callable[[Grid, Coords], Any]

DEFAULT_GRID_WIDTH_CELLS = 9
DEFAULT_CELL_WIDTH_PIXELS = 50
GRID_WIDTH_PIXELS = DEFAULT_GRID_WIDTH_CELLS * DEFAULT_CELL_WIDTH_PIXELS
EMPTY_CELL_VALUE = 0
DIGIT_FONT = ('Helvetica', '30')
class Labels:
    STATE_ATTR = 'state'
    TEXT_ATTR = 'text'
    LOAD_BTN_TEXT = 'Load'
    STORE_BTN_TEXT = 'Store'
    START_BTN_TEXT = 'Start'
    RESET_BTN_TEXT = 'Reset'
    RANDOMIZE_BTN_TEXT = 'Randomize'
    GRID_CANVAS_NAME = 'grid_canvas'
    WHITE_COLOR = 'white'
    BLACK_COLOR = 'black'
    WINDOW_NAME = 'Sudoku'

""" BEGIN: PEERS"""
def get_bound_box(coords: Coords, grid_size: int) -> tuple[int, int, int]:
    y, x = coords
    box_width = int(math.sqrt(grid_size))
    return y - (y % box_width), x - (x % box_width), box_width


def get_peers(grid: Grid, coords: Coords) -> set[int]:
    y0, x0 = coords
    # row
    s = {cell.get() for x, cell in enumerate(grid[y0]) if x != x0}
    # col
    s |= {row[x0].get() for y, row in enumerate(grid) if y != y0}
    # box
    top, left, box_size = get_bound_box((y0, x0), len(grid))
    for y in range(top, top + box_size):
        for x in range(left, left + box_size):
            if y != y0 and x != x0:
                s.add(grid[y][x].get())
    return s
""" END """

""" BEGIN: DIVISIONS """
def cols(grid: Grid) -> Grid:
    # transposes the grid
    return list(map(list, zip(*grid)))


def boxes(grid: Grid) -> Grid:
    grid_width_boxes = box_width_cells = int(math.sqrt(len(grid)))
    # (y, x) is the top-left corner of a box
    box_list = []
    for y0 in range(0, len(grid), grid_width_boxes):
        for x0 in range(0, len(grid), grid_width_boxes):
            box = []
            for y in range(y0, y0 + box_width_cells):
                box.extend(grid[y][x0:x0+box_width_cells])
            box_list.append(box)
    return box_list
""" END """

""" BEGIN: SOLVE """
def solve(
        grid: Grid,
        y0: int = 0,
        x0: int = 0,
) -> bool:
    # starts iterating at cell from recursion level
    for y in range(y0, len(grid)):
        for x in range(x0 if y == y0 else 0, len(grid[y])):
            # finds the cell for this recursion level
            if grid[y][x].get() == EMPTY_CELL_VALUE:
                peer_set = get_peers(grid, (y, x))
                for digit in range(1, len(grid) + 1):
                    if digit not in peer_set:
                        grid[y][x].set(digit)
                        if solve(grid, y0=y, x0=x):
                            # if this and all subsequent cells have a valid digit (i.e. the grid has been solved)
                            return True
                # no solution, backtrack
                grid[y][x].set(EMPTY_CELL_VALUE)
                return False
    # no more empty cells
    return True


def is_solved(grid: Grid) -> bool:
    """
    Determines if a given grid is solved.
    :param grid: The grid to check
    :return: True if the grid is solved, False otherwise
    """
    all_digits = {i for i in range(1, len(grid) + 1)}
    for group in grid + cols(grid) + boxes(grid):
        unique_digits_in_group = {cell.get() for cell in group}
        if unique_digits_in_group != all_digits:
            return False
    return True
""" END """

""" BEGIN: UTIL """
def grid_to_str(grid: RawGrid) -> str:
    """
    Utility function for producing an easily readable string representation of a raw_grid.
    :param grid: The raw_grid
    :return: The produced string representation
    """
    return '\n'.join(['  '.join(map(lambda d: '•' if d == EMPTY_CELL_VALUE else str(d), row)) for row in grid])


def read_grid(filename: str) -> RawGrid:
    with open(filename) as f:
        content = f.read()
    # first character in file specifies the grid width
    width = int(content[0])
    valid_digits = {str(i) for i in range(width + 1)}
    flattened_grid = []
    for c in content[1:]:
        if not c.isspace():
            if c in valid_digits:
                flattened_grid.append(c)
            else:
                raise IOError(f'Invalid character {c=} in file.')
    if (cell_count := len(flattened_grid)) != (expected := width ** 2):
        raise ValueError(f'Expected grid of width {width} to have {expected} cells but found {cell_count}')
    return split_list(flattened_grid, width)


def write_grid(grid: RawGrid, filename: str) -> None:
    content = str(len(grid)) + '\n' + '\n'.join(['  '.join(map(str, row)) for row in grid])
    with open(filename, 'w') as f:
        f.write(content)


def empty_grid(width: int) -> list[list[int]]:
    return [[0 for _ in range(width)] for _ in range(width)]


def random_grid(width: int) -> list[list[int]]:
    return [[random.randint(0, width) for _ in range(width)] for _ in range(width)]


def split_list(lst: list[Any], max_size: int) -> list[list[Any]]:
    """
    Splits a list into sublists of the specified size. The final sublist will have [1-n] elements.
    :param lst: The list to split
    :param max_size: The length of each sublist
    :return: A list containing all the sublists.
    """
    return [lst[i:i + max_size] for i in range(0, len(lst), max_size)]
""" END"""

""" BEGIN: INTERFACE """
def on_cell_update(canvas: tk.Canvas, var: tk.IntVar, y: int, x: int) -> None:
    render_cell(canvas, var, (y, x))


# def insert_vars(raw_grid: list[list[int]], master: tk.Tk) -> Grid:
#     grid = []
#     for y, raw_row in enumerate(raw_grid):
#         row = []
#         for x, cell in enumerate(raw_row):
#             cell_var = tk.IntVar(master=master, value=cell, name=f'cell({y},{x})')
#             cell_var.trace_add('write', lambda *_, var=cell_var, cell_y=y, cell_x=x: on_cell_update(master, var, cell_y, cell_x))
#             row.append(cell_var)
#         grid.append(row)
#     return grid


def cell_tag_for(coords: Coords) -> str:
    return f'{coords[0]},{coords[1]}'


def center_of_cell(coord: int) -> float:
    return coord * DEFAULT_CELL_WIDTH_PIXELS + DEFAULT_CELL_WIDTH_PIXELS / 2


def render_cell(canvas: tk.Canvas, cell: tk.IntVar, coords: Coords) -> None:
    canvas.delete(cell_tag_for(coords))
    if cell.get() == 0:
        return
    canvas.create_text(
        center_of_cell(coords[1]),
        center_of_cell(coords[0]),
        text=str(cell.get()),
        font=DIGIT_FONT,
        tags=cell_tag_for(coords)
    )


def render_grid(canvas: tk.Canvas, grid: Grid) -> None:
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            render_cell(canvas, cell, (y, x))


def render_grid_lines(canvas: tk.Canvas, grid_width_cells: int):
    for line_number in range(0, grid_width_cells + 1):
        coord = line_number * DEFAULT_CELL_WIDTH_PIXELS
        # top and left lines must be thicker because they're cut off
        line_width = (9 if line_number == 0 else 3) if line_number % 3 == 0 else 1
        for coords in ((coord, 0, coord, GRID_WIDTH_PIXELS), (0, coord, GRID_WIDTH_PIXELS, coord)):
            canvas.create_line(coords, fill=Labels.BLACK_COLOR, width=line_width)


def create_empty_cell(canvas: tk.Canvas, y: int, x: int) -> Any:
    cell_var = tk.IntVar(master=canvas, value=EMPTY_CELL_VALUE, name=f'cell({y}, {x})')
    cell_var.trace_add('write', lambda *_, var=cell_var, y_coord=y, x_coord=x: on_cell_update(canvas, var, y_coord, x_coord))
    return cell_var


def create_empty_grid(canvas: tk.Canvas, width: int) -> Grid:
    return [[create_empty_cell(canvas, y, x) for x in range(width)] for y in range(width)]


def dump_grid_values(grid: Grid) -> RawGrid:
    return [[cell.get() for cell in row] for row in grid]


def run() -> None:
    window = tk.Tk()
    window.title(Labels.WINDOW_NAME)

    canvas = tk.Canvas(window, name=Labels.GRID_CANVAS_NAME, background=Labels.WHITE_COLOR, width=GRID_WIDTH_PIXELS, height=GRID_WIDTH_PIXELS)

    grid = create_empty_grid(canvas, DEFAULT_GRID_WIDTH_CELLS)
    raw_grid = dump_grid_values(grid)
    render_grid_lines(canvas, DEFAULT_GRID_WIDTH_CELLS)
    render_grid(canvas, grid)

    def load():
        filename = filedialog.askopenfilename(filetypes=(('text files', '*.txt'),))
        new_raw_grid = read_grid(filename)
        for y, row in enumerate(grid):
            raw_grid[y][:] = new_raw_grid[y]
            for x, cell in enumerate(row):
                cell.set(new_raw_grid[y][x])

    def store():
        filename = filedialog.asksaveasfilename(filetypes=(('text files', '*.txt'),))
        grid_values = dump_grid_values(grid)
        write_grid(grid_values, filename)


    def start():
        for button in (load_button, store_button, start_button, reset_button, randomize_button):
            button[Labels.STATE_ATTR] = tk.DISABLED
        solved = solve(grid)
        if not solved:
            messagebox.showerror('', 'This puzzle is not solvable.')
        for button in (load_button, store_button, start_button, reset_button, randomize_button):
            button[Labels.STATE_ATTR] = tk.NORMAL

    def reset():
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                cell.set(raw_grid[y][x])

    def randomize():
        new_raw_grid = random_grid(len(grid))
        for y, row in enumerate(grid):
            raw_grid[y][:] = new_raw_grid[y]
            for x, cell in enumerate(row):
                cell.set(new_raw_grid[y][x])

    # left_frame = ttk.Frame(window)
    right_frame = ttk.Frame(window)

    load_button = ttk.Button(right_frame, text=Labels.LOAD_BTN_TEXT, command=load)
    store_button = ttk.Button(right_frame, text=Labels.STORE_BTN_TEXT, command=store)
    start_button = ttk.Button(right_frame, text=Labels.START_BTN_TEXT, command=lambda: threading.Thread(target=start).start())
    reset_button = ttk.Button(right_frame, text=Labels.RESET_BTN_TEXT, command=reset)
    randomize_button = ttk.Button(right_frame, text=Labels.RANDOMIZE_BTN_TEXT, command=randomize)

    for i, button in enumerate((load_button, store_button, start_button, reset_button, randomize_button)):
        button.grid(row=i, column=0, pady=(10 if i == 0 else 0, 10), padx=(7, 10))

    canvas.grid(row=0, column=0)
    right_frame.grid(row=0, column=1, sticky=tk.N)

    window.mainloop()
""" END """

if __name__ == '__main__':
    run()