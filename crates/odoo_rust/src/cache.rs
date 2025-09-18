//! Rust/PyO3 accelerator for Odoo ORM field cache access hot paths.
//!
//! Uses raw CPython C-API (`pyo3::ffi`) internally to minimize per-operation
//! overhead.  Safe PyO3 variants are kept as `_safe` functions for
//! documentation and semantic comparison.
//!
//! Design invariants:
//! - Sentinel comparison uses pointer identity (`==`), NOT Python `__eq__`.
//! - `PyDict_GetItem` returns borrowed refs — no refcount on lookup.
//! - `PyTuple_GET_ITEM` skips bounds checks — caller guarantees valid indices.
//! - The functions work with raw Python dicts — no Odoo imports in Rust.
//!
//! Python 3.14 notes:
//! - `PyDict_GetItem` returns borrowed refs and is safe under the GIL.
//!   For free-threaded builds, these would need `PyDict_GetItemRef` (strong
//!   refs) and careful synchronization — tracked separately.

use pyo3::ffi;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};

/// Batch cache lookup for `mapped()` and `grouped()` identity-type fast paths.
///
/// For each id in `ids`, looks up `field_cache[id]`:
/// - Cache hit (not `pending`): appends value (or `none_val` if value is None).
/// - Cache miss or `pending`: appends `none_val` placeholder, records index.
///
/// Returns `(results: list, miss_indices: list[int])`.
#[pyfunction]
pub fn batch_cache_get<'py>(
    py: Python<'py>,
    field_cache: &Bound<'py, PyDict>,
    ids: &Bound<'py, PyTuple>,
    pending: &Bound<'py, PyAny>,
    none_val: &Bound<'py, PyAny>,
) -> PyResult<(Py<PyList>, Py<PyList>)> {
    let n = ids.len() as ffi::Py_ssize_t;
    let none_py = py.None();

    // SAFETY: All pointers are borrowed from live Python objects with 'py
    // lifetime.  PyDict_GetItem returns borrowed refs (no refcount on lookup).
    // PyList_SET_ITEM steals one owned reference per slot.
    unsafe {
        let cache_ptr = field_cache.as_ptr();
        let ids_ptr = ids.as_ptr();
        let pending_ptr = pending.as_ptr();
        let none_val_ptr = none_val.as_ptr();
        let none_ptr = none_py.as_ptr();

        let result = ffi::PyList_New(n);
        if result.is_null() {
            return Err(PyErr::fetch(py));
        }

        let mut miss_items: Vec<ffi::Py_ssize_t> = Vec::new();

        for i in 0..n {
            let id_obj = ffi::PyTuple_GET_ITEM(ids_ptr, i);
            let value = ffi::PyDict_GetItem(cache_ptr, id_obj);

            if value.is_null() || value == pending_ptr {
                // Cache miss or PENDING sentinel
                ffi::Py_INCREF(none_val_ptr);
                ffi::PyList_SET_ITEM(result, i, none_val_ptr);
                miss_items.push(i);
            } else if value == none_ptr {
                // Cache hit but value is None — substitute none_val
                ffi::Py_INCREF(none_val_ptr);
                ffi::PyList_SET_ITEM(result, i, none_val_ptr);
            } else {
                // Cache hit with real value
                ffi::Py_INCREF(value);
                ffi::PyList_SET_ITEM(result, i, value);
            }
        }

        // Build miss indices list
        let miss_n = miss_items.len() as ffi::Py_ssize_t;
        let misses = ffi::PyList_New(miss_n);
        if misses.is_null() {
            ffi::Py_DECREF(result);
            return Err(PyErr::fetch(py));
        }
        for (j, &idx) in miss_items.iter().enumerate() {
            let int_obj = ffi::PyLong_FromSsize_t(idx);
            ffi::PyList_SET_ITEM(misses, j as ffi::Py_ssize_t, int_obj);
        }

        Ok((
            Bound::from_owned_ptr(py, result)
                .cast_into_unchecked::<PyList>()
                .unbind(),
            Bound::from_owned_ptr(py, misses)
                .cast_into_unchecked::<PyList>()
                .unbind(),
        ))
    }
}

/// Batch cache truthiness filter for `filtered()` field-name fast path.
///
/// For each id in `ids`, looks up `field_cache[id]`:
/// - Cache hit, not `pending`, truthy: appends id to passing list.
/// - Cache miss or `pending`: records index in miss list.
/// - Cache hit but falsy: skipped (not a miss either).
///
/// Returns `(passing_ids: list, miss_indices: list[int])`.
#[pyfunction]
pub fn batch_cache_filter<'py>(
    py: Python<'py>,
    field_cache: &Bound<'py, PyDict>,
    ids: &Bound<'py, PyTuple>,
    pending: &Bound<'py, PyAny>,
) -> PyResult<(Py<PyList>, Py<PyList>)> {
    let n = ids.len() as ffi::Py_ssize_t;

    // SAFETY: Same as batch_cache_get.  PyObject_IsTrue can call __bool__
    // but Odoo field values are immutable types (int/str/bool/float) whose
    // truthiness check is a pure C-level operation with no side effects.
    unsafe {
        let cache_ptr = field_cache.as_ptr();
        let ids_ptr = ids.as_ptr();
        let pending_ptr = pending.as_ptr();

        // Collect into Vecs first — no cleanup needed on error since
        // all pointers are borrowed (no INCREF yet).
        let mut passing: Vec<*mut ffi::PyObject> = Vec::new();
        let mut miss_items: Vec<ffi::Py_ssize_t> = Vec::new();

        for i in 0..n {
            let id_obj = ffi::PyTuple_GET_ITEM(ids_ptr, i);
            let value = ffi::PyDict_GetItem(cache_ptr, id_obj);

            if value.is_null() || value == pending_ptr {
                miss_items.push(i);
            } else {
                let truthy = ffi::PyObject_IsTrue(value);
                if truthy < 0 {
                    return Err(PyErr::fetch(py));
                }
                if truthy == 1 {
                    passing.push(id_obj);
                }
                // falsy (truthy == 0): neither pass nor miss
            }
        }

        // Build passing list
        let pass_n = passing.len() as ffi::Py_ssize_t;
        let pass_list = ffi::PyList_New(pass_n);
        if pass_list.is_null() {
            return Err(PyErr::fetch(py));
        }
        for (j, &id_ptr) in passing.iter().enumerate() {
            ffi::Py_INCREF(id_ptr);
            ffi::PyList_SET_ITEM(pass_list, j as ffi::Py_ssize_t, id_ptr);
        }

        // Build miss list
        let miss_n = miss_items.len() as ffi::Py_ssize_t;
        let miss_list = ffi::PyList_New(miss_n);
        if miss_list.is_null() {
            ffi::Py_DECREF(pass_list);
            return Err(PyErr::fetch(py));
        }
        for (j, &idx) in miss_items.iter().enumerate() {
            let int_obj = ffi::PyLong_FromSsize_t(idx);
            ffi::PyList_SET_ITEM(miss_list, j as ffi::Py_ssize_t, int_obj);
        }

        Ok((
            Bound::from_owned_ptr(py, pass_list)
                .cast_into_unchecked::<PyList>()
                .unbind(),
            Bound::from_owned_ptr(py, miss_list)
                .cast_into_unchecked::<PyList>()
                .unbind(),
        ))
    }
}

/// All-or-nothing batch cache extraction for `sorted()` fast path.
///
/// For each id in `ids`, looks up `field_cache[id]`:
/// - Cache hit (not `pending`): collects the raw value.
/// - Cache miss or `pending`: **immediately returns `None`** (early bailout).
///
/// Returns `Some(list)` with all cached values, or `None` on any miss.
/// This is the optimal pattern for `_sorted_by_ids` which needs all values
/// present to sort — a single miss means fallback to the record-based path.
#[pyfunction]
pub fn batch_cache_values<'py>(
    py: Python<'py>,
    field_cache: &Bound<'py, PyDict>,
    ids: &Bound<'py, PyTuple>,
    pending: &Bound<'py, PyAny>,
) -> PyResult<Option<Py<PyList>>> {
    let n = ids.len() as ffi::Py_ssize_t;

    // SAFETY: PyList_New initializes all slots to NULL.  On early bailout,
    // Py_DECREF on the list correctly DECREFs filled slots (0..i) and
    // skips NULL slots (i..n).
    unsafe {
        let cache_ptr = field_cache.as_ptr();
        let ids_ptr = ids.as_ptr();
        let pending_ptr = pending.as_ptr();

        let result = ffi::PyList_New(n);
        if result.is_null() {
            return Err(PyErr::fetch(py));
        }

        for i in 0..n {
            let id_obj = ffi::PyTuple_GET_ITEM(ids_ptr, i);
            let value = ffi::PyDict_GetItem(cache_ptr, id_obj);

            if value.is_null() || value == pending_ptr {
                // Miss or PENDING — bail.  Slots 0..i are owned,
                // slots i..n are NULL.  Py_DECREF handles cleanup.
                ffi::Py_DECREF(result);
                return Ok(None);
            }

            ffi::Py_INCREF(value);
            ffi::PyList_SET_ITEM(result, i, value);
        }

        Ok(Some(
            Bound::from_owned_ptr(py, result)
                .cast_into_unchecked::<PyList>()
                .unbind(),
        ))
    }
}

/// Single-record cache lookup for `_make_scalar_get` hot path.
///
/// Performs the triple dict lookup:
///   `env_dict["_field_cache_memo"][field][record_id]`
///
/// Returns the cached value if found and not `pending`.
/// Returns `sentinel` on any miss (KeyError at any level) or if `pending`.
///
/// NOTE: Not exported — the Python fallback is faster on the hit path.
/// Python's `dict[key]` compiles to `BINARY_SUBSCR` → C-level `PyDict_GetItem`,
/// so 3 subscripts = 3 C-level lookups with zero Python overhead.  The PyO3
/// function-call boundary adds ~35ns that exceeds any savings.  Kept as
/// documentation of the ffi approach.
#[allow(dead_code)]
fn scalar_cache_get<'py>(
    py: Python<'py>,
    env_dict: &Bound<'py, PyDict>,
    field: &Bound<'py, PyAny>,
    record_id: &Bound<'py, PyAny>,
    pending: &Bound<'py, PyAny>,
    sentinel: &Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyAny>> {
    let memo_key_ptr = pyo3::intern!(py, "_field_cache_memo").as_ptr();

    // SAFETY: All pointers are borrowed from live Python objects with 'py
    // lifetime.  PyDict_GetItem returns borrowed refs (NULL on miss, no
    // exception set).  We Py_INCREF only the value we return.
    unsafe {
        let env_ptr = env_dict.as_ptr();
        let field_ptr = field.as_ptr();
        let record_id_ptr = record_id.as_ptr();
        let pending_ptr = pending.as_ptr();
        let sentinel_ptr = sentinel.as_ptr();

        // Level 1: env_dict["_field_cache_memo"]
        let memo = ffi::PyDict_GetItem(env_ptr, memo_key_ptr);
        if memo.is_null() {
            ffi::Py_INCREF(sentinel_ptr);
            return Ok(Bound::from_owned_ptr(py, sentinel_ptr));
        }

        // Level 2: memo[field]
        let field_cache = ffi::PyDict_GetItem(memo, field_ptr);
        if field_cache.is_null() {
            ffi::Py_INCREF(sentinel_ptr);
            return Ok(Bound::from_owned_ptr(py, sentinel_ptr));
        }

        // Level 3: field_cache[record_id]
        let value = ffi::PyDict_GetItem(field_cache, record_id_ptr);
        if value.is_null() || value == pending_ptr {
            ffi::Py_INCREF(sentinel_ptr);
            return Ok(Bound::from_owned_ptr(py, sentinel_ptr));
        }

        ffi::Py_INCREF(value);
        Ok(Bound::from_owned_ptr(py, value))
    }
}

// ── Safe PyO3 variants (documentation / semantic reference) ─────────────

/// Safe variant of `batch_cache_get` using checked PyO3 APIs.
/// ~1.5-2x slower due to Bound wrappers and refcount on every get_item.
#[allow(dead_code)]
fn batch_cache_get_safe<'py>(
    py: Python<'py>,
    field_cache: &Bound<'py, PyDict>,
    ids: &Bound<'py, PyTuple>,
    pending: &Bound<'py, PyAny>,
    none_val: &Bound<'py, PyAny>,
) -> PyResult<(Py<PyList>, Py<PyList>)> {
    let n = ids.len();
    let mut result_items: Vec<Bound<'py, PyAny>> = Vec::with_capacity(n);
    let mut miss_items: Vec<i64> = Vec::new();

    for i in 0..n {
        let id_obj = ids.get_item(i)?;
        match field_cache.get_item(&id_obj)? {
            Some(value) => {
                if value.is(pending) {
                    result_items.push(none_val.clone());
                    miss_items.push(i as i64);
                } else if value.is_none() {
                    result_items.push(none_val.clone());
                } else {
                    result_items.push(value);
                }
            }
            None => {
                result_items.push(none_val.clone());
                miss_items.push(i as i64);
            }
        }
    }

    let results = PyList::new(py, &result_items)?;
    let misses = PyList::new(py, &miss_items)?;
    Ok((results.unbind(), misses.unbind()))
}

/// Safe variant of `batch_cache_filter` using checked PyO3 APIs.
#[allow(dead_code)]
fn batch_cache_filter_safe<'py>(
    py: Python<'py>,
    field_cache: &Bound<'py, PyDict>,
    ids: &Bound<'py, PyTuple>,
    pending: &Bound<'py, PyAny>,
) -> PyResult<(Py<PyList>, Py<PyList>)> {
    let n = ids.len();
    let mut passing: Vec<Bound<'py, PyAny>> = Vec::new();
    let mut miss_items: Vec<i64> = Vec::new();

    for i in 0..n {
        let id_obj = ids.get_item(i)?;
        match field_cache.get_item(&id_obj)? {
            Some(value) => {
                if value.is(pending) {
                    miss_items.push(i as i64);
                } else if value.is_truthy()? {
                    passing.push(id_obj);
                }
            }
            None => {
                miss_items.push(i as i64);
            }
        }
    }

    let passing_list = PyList::new(py, &passing)?;
    let misses = PyList::new(py, &miss_items)?;
    Ok((passing_list.unbind(), misses.unbind()))
}

/// Safe variant of `batch_cache_values` using checked PyO3 APIs.
#[allow(dead_code)]
fn batch_cache_values_safe<'py>(
    py: Python<'py>,
    field_cache: &Bound<'py, PyDict>,
    ids: &Bound<'py, PyTuple>,
    pending: &Bound<'py, PyAny>,
) -> PyResult<Option<Py<PyList>>> {
    let n = ids.len();
    let mut values: Vec<Bound<'py, PyAny>> = Vec::with_capacity(n);

    for i in 0..n {
        let id_obj = ids.get_item(i)?;
        match field_cache.get_item(&id_obj)? {
            Some(value) if !value.is(pending) => values.push(value),
            _ => return Ok(None),
        }
    }

    Ok(Some(PyList::new(py, &values)?.unbind()))
}

/// Safe variant of `scalar_cache_get` using checked PyO3 APIs.
/// ~3-4x slower due to Bound wrappers, get_item refcount, and cast checks.
#[allow(dead_code)]
fn scalar_cache_get_safe<'py>(
    env_dict: &Bound<'py, PyDict>,
    field: &Bound<'py, PyAny>,
    record_id: &Bound<'py, PyAny>,
    pending: &Bound<'py, PyAny>,
    sentinel: &Bound<'py, PyAny>,
) -> PyResult<Bound<'py, PyAny>> {
    let memo = match env_dict.get_item(pyo3::intern!(env_dict.py(), "_field_cache_memo"))? {
        Some(m) => m,
        None => return Ok(sentinel.clone()),
    };
    let memo_dict = memo.cast::<PyDict>()?;
    let field_cache = match memo_dict.get_item(field)? {
        Some(fc) => fc,
        None => return Ok(sentinel.clone()),
    };
    let fc_dict = field_cache.cast::<PyDict>()?;
    match fc_dict.get_item(record_id)? {
        Some(value) => {
            if value.is(pending) {
                Ok(sentinel.clone())
            } else {
                Ok(value)
            }
        }
        None => Ok(sentinel.clone()),
    }
}
