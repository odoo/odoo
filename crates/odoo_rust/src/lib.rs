//! Rust-accelerated hot paths for the Odoo ORM.
//!
//! Each submodule targets a specific Python function that was benchmarked
//! and identified as a bottleneck.  The Python wrapper imports from this
//! extension with a fallback to the pure-Python originals.
//!
//! Submodules:
//! - `clone`: Fast deep-clone for JSON-like data (replaces copy.deepcopy)
//! - `cache`: Batch cache lookups for mapped/filtered/scalar field access
//! - `ids`: Origin ID extraction for NewId-aware record collections
//! - `rows`: Cursor dictfetchall/dictfetchmany acceleration
//! - `web`: CSV export with QUOTE_ALL formatting and cell sanitization

use pyo3::prelude::*;

mod cache;
mod clone;
mod ids;
mod prefetch;
mod rows;
mod scan;
mod web;

/// The Python module exported as `odoo_rust`.
#[pymodule]
fn odoo_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // clone
    m.add_function(wrap_pyfunction!(clone::fast_clone, m)?)?;
    // cache (scalar_cache_get intentionally not exported — the Python
    // fallback is faster on the hit path due to PyO3 boundary overhead)
    m.add_function(wrap_pyfunction!(cache::batch_cache_get, m)?)?;
    m.add_function(wrap_pyfunction!(cache::batch_cache_filter, m)?)?;
    m.add_function(wrap_pyfunction!(cache::batch_cache_values, m)?)?;
    // ids
    m.add_function(wrap_pyfunction!(ids::origin_ids, m)?)?;
    // prefetch
    m.add_function(wrap_pyfunction!(prefetch::to_prefetch_ids, m)?)?;
    // rows
    m.add_function(wrap_pyfunction!(rows::rows_to_dicts, m)?)?;
    // web
    m.add_function(wrap_pyfunction!(web::csv_export, m)?)?;
    // scan (parallel file scanning for lint tests)
    m.add_function(wrap_pyfunction!(scan::scan_byte_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(scan::scan_regex_patterns, m)?)?;
    Ok(())
}
