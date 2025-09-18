//! Rust-accelerated CSV export for the Odoo web module.
//!
//! Replaces Python's `csv.writer` + per-cell sanitization loop with a single
//! Rust function that produces the complete CSV output directly.
//!
//! The Python `CSVExport.from_data()` does:
//! 1. Create a `csv.writer(fp, quoting=QUOTE_ALL)`
//! 2. For each cell: `None`/`False` → `""`, `bytes` → decode, formula protect
//! 3. `writer.writerow(...)` per row
//!
//! This module collapses all three into one pass over the data, producing the
//! final CSV string with RFC 4180 QUOTE_ALL formatting.

use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyList, PyString};

/// Generate a complete CSV string with QUOTE_ALL formatting.
///
/// Handles the same cell sanitization as Python's `CSVExport.from_data`:
/// - `None` / `False` → empty string
/// - `bytes` → UTF-8 decode
/// - Strings starting with `=`, `-`, `+` → prefix with `'` (formula protection)
/// - All other types → `str()` conversion
/// - Every cell is double-quoted with embedded `"` doubled (RFC 4180 / QUOTE_ALL)
///
/// Returns the complete CSV as a string with `\r\n` line terminators.
#[pyfunction]
pub fn csv_export(
    py: Python<'_>,
    headers: &Bound<'_, PyList>,
    rows: &Bound<'_, PyList>,
) -> PyResult<String> {
    let n_rows = rows.len();
    let n_cols = headers.len();

    // Python's False singleton for identity comparison (matches `d is False`)
    let py_false = PyBool::new(py, false).to_owned().into_any();

    // Pre-allocate: ~30 bytes per cell is a reasonable estimate for typical exports
    let capacity = (n_rows + 1) * n_cols.max(1) * 30;
    let mut buf = String::with_capacity(capacity);

    // ── Header row ──────────────────────────────────────────────────────
    for i in 0..n_cols {
        if i > 0 {
            buf.push(',');
        }
        let header = headers.get_item(i)?;
        write_quoted(&mut buf, header.cast::<PyString>()?.to_str()?);
    }
    buf.push_str("\r\n");

    // ── Data rows ───────────────────────────────────────────────────────
    for row_idx in 0..n_rows {
        let row = rows.get_item(row_idx)?;
        let row_list = row.cast::<PyList>()?;
        let row_len = row_list.len();

        for col_idx in 0..row_len {
            if col_idx > 0 {
                buf.push(',');
            }
            let cell = row_list.get_item(col_idx)?;
            write_cell(&mut buf, &cell, &py_false)?;
        }
        buf.push_str("\r\n");
    }

    Ok(buf)
}

/// Serialize a single cell value into the CSV buffer.
///
/// Matches the exact semantics of the Python sanitization loop:
/// ```python
/// if d is None or d is False:
///     d = ''
/// elif isinstance(d, bytes):
///     d = d.decode()
/// if isinstance(d, str) and d.startswith(('=', '-', '+')):
///     d = "'" + d
/// ```
fn write_cell(
    buf: &mut String,
    cell: &Bound<'_, PyAny>,
    py_false: &Bound<'_, PyAny>,
) -> PyResult<()> {
    // None or False → empty quoted cell
    // Uses identity comparison (`is`), not equality — 0 and "" pass through
    if cell.is_none() || cell.is(py_false) {
        buf.push_str("\"\"");
        return Ok(());
    }

    // String: apply formula protection, then quote
    if let Ok(s) = cell.cast::<PyString>() {
        let val = s.to_str()?;
        write_string_cell(buf, val);
        return Ok(());
    }

    // Bytes: decode UTF-8, then treat as string (with formula protection)
    if let Ok(b) = cell.cast::<PyBytes>() {
        let val = std::str::from_utf8(b.as_bytes())
            .map_err(|e| pyo3::exceptions::PyUnicodeDecodeError::new_err(e.to_string()))?;
        write_string_cell(buf, val);
        return Ok(());
    }

    // All other types (int, float, bool True, datetime, date, list, etc.)
    // → str() conversion, NO formula protection (original only checks isinstance(d, str))
    let s = cell.str()?;
    write_quoted(buf, s.to_str()?);
    Ok(())
}

/// Write a string cell with formula protection.
///
/// Spreadsheet apps interpret cells starting with `=`, `-`, or `+` as formulas.
/// Prefixing with `'` prevents this (CSV injection / formula injection defense).
#[inline]
fn write_string_cell(buf: &mut String, val: &str) {
    if !val.is_empty() && matches!(val.as_bytes()[0], b'=' | b'-' | b'+') {
        buf.push('"');
        buf.push('\'');
        write_escaped(buf, val);
        buf.push('"');
    } else {
        write_quoted(buf, val);
    }
}

/// Write a double-quoted CSV field (RFC 4180 QUOTE_ALL).
#[inline]
fn write_quoted(buf: &mut String, s: &str) {
    buf.push('"');
    write_escaped(buf, s);
    buf.push('"');
}

/// Write field content, doubling any embedded double quotes per RFC 4180.
///
/// Fast path: if no `"` present, append the string directly (most common case).
/// Slow path: replace `"` with `""` (allocates, but rare in practice).
#[inline]
fn write_escaped(buf: &mut String, s: &str) {
    if s.contains('"') {
        buf.push_str(&s.replace('"', "\"\""));
    } else {
        buf.push_str(s);
    }
}
