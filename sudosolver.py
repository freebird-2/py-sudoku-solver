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
    LOAD_BTN_TEXT = 'Load from file'
    STORE_BTN_TEXT = 'Save to file'
    START_BTN_TEXT = 'Start'
    RESET_BTN_TEXT = 'Reset'
    CLEAR_BTN_TEXT = 'Clear'
    GRID_CANVAS_NAME = 'grid_canvas'
    WHITE_COLOR = 'white'
    BLACK_COLOR = 'black'
    YELLOW_COLOR = 'yellow'
    WINDOW_NAME = 'Sudoku'

highlighted_cell: Coords = None

digits = set(range(1, DEFAULT_GRID_WIDTH_CELLS + 1))
digits_with_zero = set(range(DEFAULT_GRID_WIDTH_CELLS + 1))

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

def is_valid_puzzle(grid: Grid) -> bool:
    for group in grid + cols(grid) + boxes(grid):
        digits_in_group = [cell.get() for cell in group if cell.get() != EMPTY_CELL_VALUE]
        if len(digits_in_group) != len(set(digits_in_group)):
            return False
    return True
""" END """

""" BEGIN: UTIL """
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
def get_cell_text_tag(cell_x: int, cell_y: int) -> str:
    return f'cell_text{cell_x},{cell_y}'

def get_cell_rect_tag(cell_x: int, cell_y: int) -> str:
    return f'cell_rect({cell_x},{cell_y})'

def center_of_cell(cell_x: int, cell_y: int) -> tuple[float, float]:
    return (cell_x * DEFAULT_CELL_WIDTH_PIXELS + DEFAULT_CELL_WIDTH_PIXELS / 2,
            cell_y * DEFAULT_CELL_WIDTH_PIXELS + DEFAULT_CELL_WIDTH_PIXELS / 2)

def render_cell(canvas: tk.Canvas, cell: tk.IntVar, cell_x: int, cell_y: int) -> None:
    cell_text_tag = get_cell_text_tag(cell_x, cell_y)
    if cell.get() == 0:
        canvas.itemconfigure(cell_text_tag, text=' ')
    else:
        canvas.itemconfigure(cell_text_tag, text=str(cell.get()))

def render_grid_lines(canvas: tk.Canvas, grid_width_cells: int):
    for line_number in range(0, grid_width_cells + 1):
        coord = line_number * DEFAULT_CELL_WIDTH_PIXELS
        # top and left lines must be thicker because they're cut off
        line_width = (9 if line_number == 0 else 3) if line_number % 3 == 0 else 1
        for coords in ((coord, 0, coord, GRID_WIDTH_PIXELS), (0, coord, GRID_WIDTH_PIXELS, coord)):
            canvas.create_line(coords, fill=Labels.BLACK_COLOR, width=line_width)


def create_empty_cell(canvas: tk.Canvas, x: int, y: int) -> Any:
    cell_var = tk.IntVar(master=canvas, value=EMPTY_CELL_VALUE, name=f'cell({y}, {x})')
    cell_var.trace_add('write', lambda *_, var=cell_var, x_coord=x, y_coord=y: render_cell(canvas, var, x_coord, y_coord))
    return cell_var


def create_empty_grid(canvas: tk.Canvas, width: int) -> Grid:
    return [[create_empty_cell(canvas, x, y) for x in range(width)] for y in range(width)]


def dump_grid_values(grid: Grid) -> RawGrid:
    return [[cell.get() for cell in row] for row in grid]

def cell_at(pixel_x: int, pixel_y: int) -> Coords:
    return (pixel_x // DEFAULT_CELL_WIDTH_PIXELS, pixel_y // DEFAULT_CELL_WIDTH_PIXELS)

def get_next_cell(cell_x: int, cell_y: int, grid_width_cells: int) -> Coords:
    next_cell_x = (cell_x + 1) % grid_width_cells
    next_cell_y = ((cell_y + 1) % grid_width_cells) if next_cell_x == 0 else cell_y
    return (next_cell_x, next_cell_y)

def get_prev_cell(cell_x: int, cell_y: int, grid_width_cells: int) -> Coords:
    prev_cell_x = (cell_x - 1) % grid_width_cells
    prev_cell_y = ((cell_y - 1) % grid_width_cells) if prev_cell_x == (grid_width_cells - 1) else cell_y
    return (prev_cell_x, prev_cell_y)

def color_cell_bg(canvas: tk.Canvas, cell_x: int, cell_y: int, color: str):
    canvas.itemconfigure(get_cell_rect_tag(cell_x, cell_y), fill=color)

def create_cell_rects(canvas, grid_width_cells: int):
    for cell_x in range(grid_width_cells):
        for cell_y in range(grid_width_cells):
            pixel_x = cell_x * DEFAULT_CELL_WIDTH_PIXELS
            pixel_y = cell_y * DEFAULT_CELL_WIDTH_PIXELS
            canvas.create_rectangle(
                    pixel_x,
                    pixel_y,
                    pixel_x + DEFAULT_CELL_WIDTH_PIXELS,
                    pixel_y + DEFAULT_CELL_WIDTH_PIXELS,
                    fill='white',
                    tags=get_cell_rect_tag(cell_x, cell_y)
            )

def create_cell_texts(canvas, grid_width_cells: int):
    for cell_x in range(grid_width_cells):
        for cell_y in range(grid_width_cells):
            center_pixel_x, center_pixel_y = center_of_cell(cell_x, cell_y)
            canvas.create_text(
                center_pixel_x,
                center_pixel_y,
                text=' ',
                font=DIGIT_FONT,
                tags=get_cell_text_tag(cell_x, cell_y)
            )


def run() -> None:
    window = tk.Tk()
    window.title(Labels.WINDOW_NAME)

    canvas = tk.Canvas(window, name=Labels.GRID_CANVAS_NAME, background=Labels.WHITE_COLOR, width=GRID_WIDTH_PIXELS, height=GRID_WIDTH_PIXELS)

    grid = create_empty_grid(canvas, DEFAULT_GRID_WIDTH_CELLS)
    create_cell_rects(canvas, DEFAULT_GRID_WIDTH_CELLS)
    create_cell_texts(canvas, DEFAULT_GRID_WIDTH_CELLS)
    raw_grid = dump_grid_values(grid)
    render_grid_lines(canvas, DEFAULT_GRID_WIDTH_CELLS)

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
        for button in (load_button, store_button, start_button, reset_button, clear_button):
            button[Labels.STATE_ATTR] = tk.DISABLED
        if not is_valid_puzzle(grid):
            messagebox.showerror('', 'This puzzle is not solvable (invalid initial conditions).')
        else:
            solved = solve(grid)
            if not solved:
                messagebox.showerror('', 'This puzzle is not solvable.')
        for button in (load_button, store_button, start_button, reset_button, clear_button):
            button[Labels.STATE_ATTR] = tk.NORMAL

    def reset():
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                cell.set(raw_grid[y][x])

    def clear():
        raw_grid = empty_grid(DEFAULT_GRID_WIDTH_CELLS)
        for row in grid:
            for cell in row:
                cell.set(0)

    def handle_key_press(event):
        keysym = event.keysym
        global highlighted_cell
        if highlighted_cell is None:
            return
        hl_cell_x, hl_cell_y = highlighted_cell
        if keysym in ('Up', 'Down', 'Left', 'Right'):
            if keysym == 'Up' and hl_cell_y > 0:
                hl_cell_y -= 1
            elif keysym == 'Down' and hl_cell_y < (DEFAULT_GRID_WIDTH_CELLS - 1):
                hl_cell_y += 1
            elif keysym == 'Left' and hl_cell_x > 0:
                hl_cell_x -= 1
            elif keysym == 'Right' and hl_cell_x < (DEFAULT_GRID_WIDTH_CELLS - 1):
                hl_cell_x += 1
            change_hl_cell(canvas, hl_cell_x, hl_cell_y)
        elif keysym in (str(n) for n in range(DEFAULT_GRID_WIDTH_CELLS + 1)):
            grid[hl_cell_y][hl_cell_x].set(int(keysym))
            next_cell_x, next_cell_y = get_next_cell(*highlighted_cell, DEFAULT_GRID_WIDTH_CELLS)
            change_hl_cell(canvas, next_cell_x, next_cell_y)
        elif keysym == 'space':
            grid[hl_cell_y][hl_cell_x].set(0)
            next_cell_x, next_cell_y = get_next_cell(*highlighted_cell, DEFAULT_GRID_WIDTH_CELLS)
            change_hl_cell(canvas, next_cell_x, next_cell_y)
        elif keysym == 'BackSpace':
            grid[hl_cell_y][hl_cell_x].set(0)
            prev_cell_x, prev_cell_y = get_prev_cell(*highlighted_cell, DEFAULT_GRID_WIDTH_CELLS)
            change_hl_cell(canvas, prev_cell_x, prev_cell_y)

    def change_hl_cell(canvas, new_hl_cell_x: int, new_hl_cell_y: int):
        global highlighted_cell
        if (new_hl_cell_x, new_hl_cell_y) == highlighted_cell:
            return
        if highlighted_cell is not None:
            color_cell_bg(canvas, *highlighted_cell, 'white')
        color_cell_bg(canvas, new_hl_cell_x, new_hl_cell_y, 'yellow')
        highlighted_cell = (new_hl_cell_x, new_hl_cell_y)

    def handle_click(event):
        global highlighted_cell
        clicked_cell_x, clicked_cell_y = cell_at(event.x, event.y)
        change_hl_cell(canvas, clicked_cell_x, clicked_cell_y)

    right_frame = ttk.Frame(window)

    load_button = ttk.Button(right_frame, text=Labels.LOAD_BTN_TEXT, command=load)
    store_button = ttk.Button(right_frame, text=Labels.STORE_BTN_TEXT, command=store)
    start_button = ttk.Button(right_frame, text=Labels.START_BTN_TEXT, command=lambda: threading.Thread(target=start).start())
    reset_button = ttk.Button(right_frame, text=Labels.RESET_BTN_TEXT, command=reset)
    clear_button = ttk.Button(right_frame, text=Labels.CLEAR_BTN_TEXT, command=clear)


    for i, button in enumerate((load_button, store_button, start_button, reset_button, clear_button)):
        button.grid(row=i, column=0, pady=(10 if i == 0 else 0, 10), padx=(7, 10))

    canvas.grid(row=0, column=0)
    right_frame.grid(row=0, column=1, sticky=tk.N)

    window.bind("<Key>", handle_key_press)
    canvas.bind("<Button-1>", handle_click)

    window.mainloop()
""" END """

if __name__ == '__main__':
    run()
