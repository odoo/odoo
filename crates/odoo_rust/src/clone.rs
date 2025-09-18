//! Fast deep-clone for JSON-like Python objects using raw CPython C-API.
//!
//! Replaces `copy.deepcopy` for JSON-like data (dict/list/tuple of scalars).
//! Uses `_PyDict_NewPresized` + `PyDict_Next` for zero-resize dict cloning,
//! and `PyList_SET_ITEM` / `PyTuple_SET_ITEM` for direct slot writes.
//!
//! The Rust version is faster because:
//! - `_PyDict_NewPresized` pre-allocates the hash table (no resizes)
//! - `PyDict_Next` iterates the internal array directly (no iterator object)
//! - `PyList_SET_ITEM` writes slots directly (no bounds check, steals ref)
//! - Type dispatch via `PyDict_CheckExact` (single pointer compare)
//! - No Python function-call overhead per recursion level
//!
//! The safe PyO3 variant is kept as `fast_clone_safe` for documentation.

use pyo3::ffi;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};

// _PyDict_NewPresized pre-allocates dict hash tables at the right size,
// avoiding resize during fill.  CPython internal API, stable since 3.3,
// used extensively by CPython itself.
unsafe extern "C" {
    fn _PyDict_NewPresized(minused: ffi::Py_ssize_t) -> *mut ffi::PyObject;
}

/// Deep-clone a JSON-like Python object (dict/list/tuple of scalars).
///
/// Dicts, lists, and tuples are recursively copied.  All other values
/// (str, int, float, bool, None) are shared by reference (zero-copy).
#[pyfunction]
pub fn fast_clone<'py>(obj: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
    let py = obj.py();
    unsafe { Ok(Bound::from_owned_ptr(py, clone_inner(py, obj.as_ptr())?)) }
}

/// Recursive deep-clone using raw CPython C-API.
///
/// SAFETY: `obj` must be a valid Python object with the GIL held.
/// Returns a new (owned) reference.  On error, all partially-constructed
/// containers are cleaned up before returning.
unsafe fn clone_inner(
    py: Python<'_>,
    obj: *mut ffi::PyObject,
) -> PyResult<*mut ffi::PyObject> {
    unsafe {
        // Dict — most common container in Odoo JSON blobs.
        // CheckExact skips subclass traversal; JSON dicts are always plain dict.
        if ffi::PyDict_CheckExact(obj) != 0 {
            let size = ffi::PyDict_Size(obj);
            let new_dict = _PyDict_NewPresized(size);
            if new_dict.is_null() {
                return Err(PyErr::fetch(py));
            }

            // PyDict_Next iterates the internal hash table directly —
            // no iterator object created, borrowed key/val refs.
            let mut pos: ffi::Py_ssize_t = 0;
            let mut key: *mut ffi::PyObject = std::ptr::null_mut();
            let mut val: *mut ffi::PyObject = std::ptr::null_mut();

            while ffi::PyDict_Next(obj, &mut pos, &mut key, &mut val) != 0 {
                let cloned_val = match clone_inner(py, val) {
                    Ok(v) => v,
                    Err(e) => {
                        ffi::Py_DECREF(new_dict);
                        return Err(e);
                    }
                };
                // PyDict_SetItem INCREFs both key and value
                if ffi::PyDict_SetItem(new_dict, key, cloned_val) < 0 {
                    ffi::Py_DECREF(cloned_val);
                    ffi::Py_DECREF(new_dict);
                    return Err(PyErr::fetch(py));
                }
                // SetItem INCREFed cloned_val, release our reference
                ffi::Py_DECREF(cloned_val);
            }

            return Ok(new_dict);
        }

        // List — second most common (JSON arrays, One2many values).
        if ffi::PyList_CheckExact(obj) != 0 {
            let n = ffi::PyList_GET_SIZE(obj);
            let new_list = ffi::PyList_New(n);
            if new_list.is_null() {
                return Err(PyErr::fetch(py));
            }

            for i in 0..n {
                let item = ffi::PyList_GET_ITEM(obj, i);
                let cloned = match clone_inner(py, item) {
                    Ok(v) => v,
                    Err(e) => {
                        // Slots 0..i owned, i..n NULL — Py_DECREF handles it
                        ffi::Py_DECREF(new_list);
                        return Err(e);
                    }
                };
                // PyList_SET_ITEM steals the reference
                ffi::PyList_SET_ITEM(new_list, i, cloned);
            }

            return Ok(new_list);
        }

        // Tuple — rare in JSON data but handled for completeness.
        if ffi::PyTuple_CheckExact(obj) != 0 {
            let n = ffi::PyTuple_GET_SIZE(obj);
            let new_tuple = ffi::PyTuple_New(n);
            if new_tuple.is_null() {
                return Err(PyErr::fetch(py));
            }

            for i in 0..n {
                let item = ffi::PyTuple_GET_ITEM(obj, i);
                let cloned = match clone_inner(py, item) {
                    Ok(v) => v,
                    Err(e) => {
                        ffi::Py_DECREF(new_tuple);
                        return Err(e);
                    }
                };
                // PyTuple_SET_ITEM steals the reference
                ffi::PyTuple_SET_ITEM(new_tuple, i, cloned);
            }

            return Ok(new_tuple);
        }

        // Leaf value (str, int, float, bool, None) — share by reference
        ffi::Py_INCREF(obj);
        Ok(obj)
    }
}

// ── Safe PyO3 variant (documentation / semantic reference) ──────────────

/// Safe variant of `fast_clone` using checked PyO3 APIs.
/// ~1.5-2x slower due to Bound wrappers, downcast checks, and iterator
/// overhead per container.
#[allow(dead_code)]
fn fast_clone_safe(obj: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    clone_inner_safe(obj)
}

#[allow(dead_code)]
fn clone_inner_safe(obj: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let py = obj.py();

    if let Ok(dict) = obj.cast::<PyDict>() {
        let new_dict = PyDict::new(py);
        for (key, value) in dict.iter() {
            let cloned_value = clone_inner_safe(&value)?;
            new_dict.set_item(key, cloned_value)?;
        }
        return Ok(new_dict.unbind().into_any());
    }

    if let Ok(list) = obj.cast::<PyList>() {
        let len = list.len();
        let mut items: Vec<Py<PyAny>> = Vec::with_capacity(len);
        for item in list.iter() {
            items.push(clone_inner_safe(&item)?);
        }
        let new_list = PyList::new(py, &items)?;
        return Ok(new_list.unbind().into_any());
    }

    if let Ok(tuple) = obj.cast::<PyTuple>() {
        let len = tuple.len();
        let mut items: Vec<Py<PyAny>> = Vec::with_capacity(len);
        for i in 0..len {
            items.push(clone_inner_safe(&tuple.get_item(i)?)?);
        }
        let new_tuple = PyTuple::new(py, &items)?;
        return Ok(new_tuple.unbind().into_any());
    }

    Ok(obj.clone().unbind())
}
