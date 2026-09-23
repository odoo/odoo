use std::fs;
use std::path::{Path, PathBuf};

const WORKSPACE_INPUTS: [&str; 2] = ["Cargo.lock", "Cargo.toml"];

fn crc32(data: &[u8]) -> u32 {
    let mut table = [0u32; 256];
    for (i, entry) in table.iter_mut().enumerate() {
        let mut c = i as u32;
        for _ in 0..8 {
            c = if c & 1 != 0 {
                0xEDB8_8320 ^ (c >> 1)
            } else {
                c >> 1
            };
        }
        *entry = c;
    }

    let mut crc = 0xFFFF_FFFF_u32;
    for &byte in data {
        crc = table[((crc ^ u32::from(byte)) & 0xFF) as usize] ^ (crc >> 8);
    }
    crc ^ 0xFFFF_FFFF
}

fn collect_rust_sources(dir: &Path, found: &mut Vec<PathBuf>) {
    let entries = fs::read_dir(dir).unwrap_or_else(|e| panic!("read_dir {}: {e}", dir.display()));
    for entry in entries {
        let path = entry.expect("dir entry").path();
        if path.is_dir() {
            collect_rust_sources(&path, found);
        } else if path.extension().is_some_and(|ext| ext == "rs") {
            found.push(path);
        }
    }
}

pub fn stamp_build_identity(prefix: &str) {
    let root = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));

    let mut sources = vec![root.join("Cargo.toml")];
    collect_rust_sources(&root.join("src"), &mut sources);

    let mut inputs: Vec<(String, PathBuf)> = sources
        .into_iter()
        .map(|path| {
            let rel = path
                .strip_prefix(&root)
                .expect("a crate source lives under the crate")
                .to_string_lossy()
                .replace('\\', "/");
            (rel, path)
        })
        .collect();
    for name in WORKSPACE_INPUTS {
        let path = root.join("..").join(name);
        println!("cargo:rerun-if-changed=../{name}");
        if path.is_file() {
            inputs.push((format!("../{name}"), path));
        }
    }
    inputs.sort_by(|a, b| a.0.cmp(&b.0));

    println!("cargo:rerun-if-changed=src");
    println!("cargo:rerun-if-changed=Cargo.toml");

    let mut blob: Vec<u8> = Vec::new();
    for (rel, path) in &inputs {
        blob.extend_from_slice(rel.as_bytes());
        blob.push(0);
        blob.extend_from_slice(&fs::read(path).unwrap_or_else(|e| panic!("read {rel}: {e}")));
        blob.push(0);
    }

    println!("cargo:rustc-env={prefix}_SOURCE_CRC={:08x}", crc32(&blob));

    let profile = std::env::var("PROFILE").expect("PROFILE");
    println!("cargo:rustc-env={prefix}_PROFILE={profile}");
}

#[cfg(test)]
mod tests {
    use super::crc32;

    #[test]
    fn crc32_matches_zlib() {
        assert_eq!(crc32(b""), 0x0000_0000);
        assert_eq!(crc32(b"a"), 0xE8B7_BE43);
        assert_eq!(crc32(b"abc"), 0x3524_41C2);
        assert_eq!(
            crc32(b"The quick brown fox jumps over the lazy dog"),
            0x414F_A339
        );
        assert_eq!(crc32(b"\x00\xff\x00\xff"), 0xB2DE_047C);
    }
}
