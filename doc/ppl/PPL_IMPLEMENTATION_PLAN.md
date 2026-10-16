# Log Keputusan Implementasi (Decision Log)

## 2026-09-07: Mapping Unit Jurnal
- **Keputusan**: Menambahkan field `journal_unit_dept` (Selection) pada model `sifnext.unit` untuk menggantikan hardcode `'pusat'` saat membuat Jurnal Besar (`create_journal_from_ppl()`).
- **Alasan**: Modul Jurnal Besar (`sif.jurnal.entry`) mewajibkan kolom departemen diisi secara dinamis sesuai cabang sekolah, bukan dikunci ke kantor pusat.
- **Konsekuensi & Upgrade Path**: Terdapat *coupling* (keterikatan) nilai `selection` pada master Unit di PPL dengan `unit_dept` milik modul `sif_keuangan`. Jika Keuangan menambah departemen baru, field `journal_unit_dept` pada modul `sifnext_ppl` harus di-update agar sinkron. Solusi ideal: `unit_dept` pada `sif_keuangan` diubah dari Selection menjadi M2O ke tabel departemen, lalu dipanggil dinamis oleh modul jembatan.