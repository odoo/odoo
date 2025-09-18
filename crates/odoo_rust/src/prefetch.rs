//! Prefetch ID selection for Field.__get__ cache misses.
//!
//! Replaces `Field._to_prefetch()` — the set-based filtering loop that selects
//! which record IDs to fetch in a single SQL query when a cache miss occurs.
//!
//! Called on *every* lazy field access (potentially 1000s of times per RPC),
//! this is one of the highest-frequency functions in the ORM.
//!
//! The Rust version is faster because:
//! - `HashSet<i64>` membership testing avoids Python's hash dispatch overhead
//! - No Python `set()` construction from dict keys (iterates C dict directly)
//! - Combined insert+check via `HashSet::insert()` (returns bool)
//! - No `bool()` coercion dispatch per ID

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use std::collections::HashSet;

/// Build the list of IDs to prefetch for a given record.
///
/// This is the computational core of `Field._to_prefetch()`:
/// 1. Start with `seen = set(field_cache.keys()) | {record_id}`
/// 2. `result = [record_id]`
/// 3. For each id in prefetch_ids (up to `prefetch_max`):
///    - If id is a positive int not in seen: append to result, mark seen
///    - Skip NewId objects (falsy) and already-seen ids
/// 4. Return result as a Python tuple (ready for `browse()`)
///
/// Returns `None` if `record_id` is not a positive integer (NewId case),
/// signaling the caller to use the Python fallback.
#[pyfunction]
pub fn to_prefetch_ids<'py>(
    py: Python<'py>,
    record_id: &Bound<'py, PyAny>,
    prefetch_ids: &Bound<'py, PyTuple>,
    field_cache: &Bound<'py, PyDict>,
    prefetch_max: usize,
) -> PyResult<Option<Py<PyTuple>>> {
    // Only handle real records (positive int IDs).
    // NewId objects fail extract::<i64>(), and id=0 is not a valid DB id.
    let rec_id: i64 = match record_id.extract() {
        Ok(id) if id > 0 => id,
        _ => return Ok(None), // Fall back to Python for NewId
    };

    // Build seen set from field_cache keys.
    // Only extract int keys — NewId keys are irrelevant when kind=True
    // (we only include IDs where bool(id) == True, i.e. positive ints).
    let cache_len = field_cache.len();
    let mut seen: HashSet<i64> = HashSet::with_capacity(cache_len + 1);
    for (key, _) in field_cache.iter() {
        if let Ok(k) = key.extract::<i64>() {
            seen.insert(k);
        }
    }
    seen.insert(rec_id);

    // Build result — reuse original PyAny references to avoid int allocation.
    let n = prefetch_ids.len();
    let capacity = prefetch_max.min(n + 1);
    let mut result: Vec<Bound<'py, PyAny>> = Vec::with_capacity(capacity);
    result.push(record_id.clone());

    for i in 0..n {
        if result.len() >= prefetch_max {
            break;
        }
        let id_obj = prefetch_ids.get_item(i)?;
        if let Ok(id_val) = id_obj.extract::<i64>() {
            // seen.insert() returns true if the value was NOT already present
            if id_val > 0 && seen.insert(id_val) {
                result.push(id_obj);
            }
        }
        // Non-int IDs (NewId) silently skipped: bool(NewId) == False != kind
    }

    // Return a tuple — browse() uses tuples directly without conversion.
    Ok(Some(PyTuple::new(py, &result)?.unbind()))
}
