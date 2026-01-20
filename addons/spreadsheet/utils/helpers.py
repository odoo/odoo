
DEFAULT_COLUMN_WIDTH = 150   # pixels, default width of a column
MIN_COLUMNS = 26             # minimum number of columns (A-Z)
MIN_ROWS = 100               # minimum number of rows


def index_to_column_letter(n):
    """Convert 0-based index to spreadsheet column letter (A, B, ..., Z, AA, AB…)."""
    if n < 0:
        raise ValueError(f"number must be positive. Got {n}")
    if n < 26:
        return chr(65 + n)
    else:
        return index_to_column_letter(n // 26 - 1) + index_to_column_letter(n % 26)


def to_cell_reference(col, row):
    """
    Convert 0-based column and row indices into spreadsheet cell reference.
    Example:
        to_cell_reference(0, 0) -> "A1"
        to_cell_reference(1, 2) -> "B3"
    """
    col_letter = index_to_column_letter(col)
    return f"{col_letter}{row + 1}"
