//! Parallel file scanner for lint tests.
//!
//! Two entry points:
//! - [`scan_byte_patterns`]: SIMD-accelerated byte-literal search (conflict markers, etc.)
//! - [`scan_regex_patterns`]: Multi-pattern regex search (JS/XML pattern detection)
//!
//! Uses [`ignore::WalkParallel`] for lock-free directory traversal and
//! [`memchr::memmem`] for SIMD-accelerated byte matching.  Typically
//! 10–50× faster than sequential Python file I/O on multi-core machines.

use std::sync::{Arc, Mutex};

use ignore::WalkBuilder;
use pyo3::prelude::*;

// ── Helpers ──────────────────────────────────────────────────────────

/// Normalize extensions: strip leading dot if present.
fn normalize_extensions(extensions: &[String]) -> Arc<[String]> {
    extensions
        .iter()
        .map(|e| e.strip_prefix('.').unwrap_or(e).to_owned())
        .collect::<Vec<_>>()
        .into()
}

/// Build a parallel walker over the given root directories.
fn make_walker(roots: &[String]) -> WalkBuilder {
    let mut builder = WalkBuilder::new(&roots[0]);
    for root in &roots[1..] {
        builder.add(root);
    }
    // Don't skip hidden files (Odoo has no meaningful dotfiles to skip),
    // and don't honour .gitignore (we want to scan everything).
    builder.hidden(false).git_ignore(false);
    builder
}

/// Check whether a directory-entry should be visited.
///
/// Returns `Skip` for excluded directories, `Continue` for non-matching
/// files, and `None` when the entry is a matching file whose `path` the
/// caller should process.
fn filter_entry(
    entry: &ignore::DirEntry,
    ext_set: &[String],
    exclude: &[String],
) -> Option<ignore::WalkState> {
    let path = entry.path();

    if entry.file_type().is_some_and(|ft| ft.is_dir()) {
        if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
            if exclude.iter().any(|ex| ex.as_str() == name) {
                return Some(ignore::WalkState::Skip);
            }
        }
        return Some(ignore::WalkState::Continue);
    }

    let ext = match path.extension().and_then(|e| e.to_str()) {
        Some(e) => e,
        None => return Some(ignore::WalkState::Continue),
    };
    if !ext_set.iter().any(|a| a.as_str() == ext) {
        return Some(ignore::WalkState::Continue);
    }

    None // entry is a matching file — caller should process it
}

// ── Byte Pattern Scanner ─────────────────────────────────────────────

/// Scan files under *roots* for byte-literal patterns.
///
/// Returns a list of ``(file_path, line_number, pattern_index)`` for every
/// occurrence found.  Line numbers are 1-based.
///
/// Example (conflict markers)::
///
///     results = scan_byte_patterns(
///         ["/srv/odoo/core"],
///         [".py", ".js", ".xml"],
///         [b"<<<<<<<", b">>>>>>>"],
///         ["node_modules", "__pycache__"],
///     )
#[pyfunction]
pub fn scan_byte_patterns(
    _py: Python<'_>,
    roots: Vec<String>,
    extensions: Vec<String>,
    patterns: Vec<Vec<u8>>,
    exclude_dirs: Vec<String>,
) -> PyResult<Vec<(String, usize, usize)>> {
    if roots.is_empty() {
        return Ok(Vec::new());
    }

    let ext_set = normalize_extensions(&extensions);
    let exclude: Arc<[String]> = exclude_dirs.into();
    let pats: Arc<[Vec<u8>]> = patterns.into();
    let results: Arc<Mutex<Vec<(String, usize, usize)>>> = Arc::default();

    // The parallel walker spawns Rust threads that never touch Python
    // objects, so holding the GIL on the calling thread is harmless.
    make_walker(&roots).build_parallel().run(|| {
        let ext_set = Arc::clone(&ext_set);
        let exclude = Arc::clone(&exclude);
        let pats = Arc::clone(&pats);
        let results = Arc::clone(&results);

        Box::new(move |entry| {
            let entry = match entry {
                Ok(e) => e,
                Err(_) => return ignore::WalkState::Continue,
            };

            if let Some(state) = filter_entry(&entry, &ext_set, &exclude) {
                return state;
            }

            let path = entry.path();
            let content = match std::fs::read(path) {
                Ok(c) => c,
                Err(_) => return ignore::WalkState::Continue,
            };

            let path_str = path.to_string_lossy().into_owned();
            let mut hits = Vec::new();

            for (idx, pat) in pats.iter().enumerate() {
                let mut start = 0;
                while let Some(pos) = memchr::memmem::find(&content[start..], pat) {
                    let abs = start + pos;
                    let line = memchr::memchr_iter(b'\n', &content[..abs]).count() + 1;
                    hits.push((path_str.clone(), line, idx));
                    start = abs + 1;
                }
            }

            if !hits.is_empty() {
                results.lock().unwrap().extend(hits);
            }

            ignore::WalkState::Continue
        })
    });

    Ok(Arc::try_unwrap(results).unwrap().into_inner().unwrap())
}

// ── Regex Pattern Scanner ────────────────────────────────────────────

/// Scan files under *roots* for regex patterns.
///
/// Returns a list of ``(file_path, line_number, pattern_index, matched_text)``
/// for every match found.  Patterns are compiled once and reused across all
/// files.  Use ``(?s)`` inline flag for dot-matches-newline (DOTALL).
///
/// Example (JS translation misuse)::
///
///     results = scan_regex_patterns(
///         ["/srv/odoo/core"],
///         [".js"],
///         [r"(?s)_t\(\s*`.*?\s*`\s*\)", r"\b_\(\s*['\"]"],
///         ["node_modules"],
///     )
#[pyfunction]
pub fn scan_regex_patterns(
    _py: Python<'_>,
    roots: Vec<String>,
    extensions: Vec<String>,
    patterns: Vec<String>,
    exclude_dirs: Vec<String>,
) -> PyResult<Vec<(String, usize, usize, String)>> {
    if roots.is_empty() {
        return Ok(Vec::new());
    }

    let regexes: Arc<[regex::Regex]> = patterns
        .iter()
        .map(|p| regex::Regex::new(p))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid regex: {e}")))?
        .into();

    let ext_set = normalize_extensions(&extensions);
    let exclude: Arc<[String]> = exclude_dirs.into();
    let results: Arc<Mutex<Vec<(String, usize, usize, String)>>> = Arc::default();

    make_walker(&roots).build_parallel().run(|| {
        let ext_set = Arc::clone(&ext_set);
        let exclude = Arc::clone(&exclude);
        let regexes = Arc::clone(&regexes);
        let results = Arc::clone(&results);

        Box::new(move |entry| {
            let entry = match entry {
                Ok(e) => e,
                Err(_) => return ignore::WalkState::Continue,
            };

            if let Some(state) = filter_entry(&entry, &ext_set, &exclude) {
                return state;
            }

            let path = entry.path();
            let content = match std::fs::read(path) {
                Ok(c) => c,
                Err(_) => return ignore::WalkState::Continue,
            };
            let text = String::from_utf8_lossy(&content);

            let path_str = path.to_string_lossy().into_owned();
            let mut hits = Vec::new();

            for (idx, re) in regexes.iter().enumerate() {
                for m in re.find_iter(&text) {
                    let line =
                        memchr::memchr_iter(b'\n', text[..m.start()].as_bytes()).count() + 1;
                    hits.push((path_str.clone(), line, idx, m.as_str().to_owned()));
                }
            }

            if !hits.is_empty() {
                results.lock().unwrap().extend(hits);
            }

            ignore::WalkState::Continue
        })
    });

    Ok(Arc::try_unwrap(results).unwrap().into_inner().unwrap())
}
