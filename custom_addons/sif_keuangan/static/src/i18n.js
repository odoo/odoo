/** @odoo-module **/

import { user } from "@web/core/user";

/**
 * SIFNEXT Accounting Bilingual Translation Dictionary (ID / EN)
 * Auto-detects user preference language (id_ID vs en_US).
 */

export const TRANSLATIONS = {
    // Top Bar Actions & Filters
    "btn.pdf": { id: "PDF", en: "PDF" },
    "btn.xlsx": { id: "XLSX", en: "XLSX" },
    "btn.expand_all": { id: "Buka Semua", en: "Expand All" },
    "btn.collapse_all": { id: "Tutup Semua", en: "Collapse All" },
    "btn.reset_search": { id: "Reset Pencarian", en: "Reset Search" },

    // Search Placeholders
    "search.gl": { id: "Cari akun / partner...", en: "Search account / partner..." },
    "search.bs": { id: "Cari akun...", en: "Search account..." },
    "search.pl": { id: "Cari akun...", en: "Search account..." },

    // Common Filter Options
    "filter.all_units": { id: "Semua Departemen", en: "All Departments" },
    "filter.all_partners": { id: "Semua Rekanan", en: "All Partners" },

    // Presets
    "preset.this_year": { id: "Tahun Ini", en: "This Year" },
    "preset.this_month": { id: "Bulan Ini", en: "This Month" },
    "preset.this_quarter": { id: "Kuartal Ini", en: "This Quarter" },
    "preset.last_month": { id: "Bulan Lalu", en: "Last Month" },
    "preset.last_year": { id: "Tahun Lalu", en: "Last Year" },
    "preset.custom": { id: "Rentang Kustom...", en: "Custom Range..." },
    "preset.custom_range": { id: "Rentang Kustom...", en: "Custom Range..." },
    "preset.custom_date": { id: "Tanggal Kustom...", en: "Custom Date..." },
    "preset.end_of_year": { id: "Akhir Tahun Ini", en: "End of This Year" },
    "preset.today": { id: "Hari Ini", en: "Today" },
    "preset.end_of_month": { id: "Akhir Bulan Ini", en: "End of This Month" },
    "preset.end_of_last_month": { id: "Akhir Bulan Lalu", en: "End of Last Month" },
    "preset.end_of_last_year": { id: "Akhir Tahun Lalu", en: "End of Last Year" },

    // Comparison Options
    "comp.none": { id: "Tanpa Pembanding", en: "No Comparison" },
    "comp.last_month": { id: "vs. Bulan Lalu", en: "vs. Last Month" },
    "comp.last_year": { id: "vs. Tahun Lalu", en: "vs. Last Year" },
    "comp.custom": { id: "vs. Tanggal Kustom...", en: "vs. Custom Date..." },
    "comp.custom_range": { id: "vs. Rentang Kustom...", en: "vs. Custom Range..." },

    // Target Move
    "move.posted": { id: "Posted Entries", en: "Posted Entries" },
    "move.all": { id: "All Entries", en: "All Entries" },
    "status.posted_only": { id: "Hanya Jurnal Disetujui", en: "Posted Only" },
    "status.all_entries": { id: "Semua Jurnal", en: "All Entries" },

    // Currency
    "currency.in_rp": { id: "In Rp", en: "In Rp" },

    // Table Headers
    "th.account_desc": { id: "AKUN / KETERANGAN TRANSAKSI", en: "ACCOUNT / TRANSACTION DESCRIPTION" },
    "th.date": { id: "TANGGAL", en: "DATE" },
    "th.voucher_journal": { id: "NO. BUKTI / JURNAL", en: "VOUCHER / JOURNAL NO." },
    "th.partner": { id: "PARTNER / REKANAN", en: "PARTNER" },
    "th.debit": { id: "DEBET (RP)", en: "DEBIT (RP)" },
    "th.credit": { id: "KREDIT (RP)", en: "CREDIT (RP)" },
    "th.balance": { id: "SALDO (RP)", en: "BALANCE (RP)" },
    "th.line_item_account": { id: "LINE ITEM / AKUN", en: "LINE ITEM / ACCOUNT" },
    "th.period": { id: "PERIODE", en: "PERIOD" },
    "th.comparison": { id: "PEMBANDING", en: "COMPARISON" },
    "th.difference": { id: "SELISIH (RP)", en: "DIFFERENCE (RP)" },
    "th.growth": { id: "%", en: "%" },

    // General Ledger View Labels
    "gl.title": { id: "General Ledger", en: "General Ledger" },
    "gl.period_prefix": { id: "Periode", en: "Period" },
    "gl.normal_debit": { id: "debet", en: "debit" },
    "gl.normal_credit": { id: "kredit", en: "credit" },
    "gl.lines": { id: "baris", en: "lines" },
    "gl.initial_balance": { id: "Saldo Awal (Initial Balance)", en: "Initial Balance" },
    "gl.total_movement": { id: "Total Mutasi Akun", en: "Total Account Movement" },
    "gl.grand_total": { id: "TOTAL GENERAL LEDGER (SELURUH AKUN)", en: "TOTAL GENERAL LEDGER (ALL ACCOUNTS)" },
    "gl.empty_title": { id: "Tidak Ada Transaksi Ditemukan", en: "No Transactions Found" },
    "gl.empty_desc": { id: "Tidak ada pergerakan entri jurnal untuk filter tanggal dan kriteria yang dipilih.", en: "No journal movements found for the selected date filter and criteria." },
    "gl.footer_accounts": { id: "Akun Terdaftar", en: "Registered Accounts" },
    "gl.footer_system": { id: "Rumus: Total Debet = Total Kredit (Selisih Mutasi Rp 0,00)", en: "Formula: Total Debit = Total Credit (Movement Diff Rp 0.00)" },
    "gl.footer_total_debit": { id: "Total Debet", en: "Total Debit" },
    "gl.footer_total_credit": { id: "Total Kredit", en: "Total Credit" },
    "gl.footer_net_diff": { id: "Net Selisih Mutasi", en: "Net Movement Difference" },

    // Balance Sheet View Labels
    "bs.title": { id: "Balance Sheet", en: "Balance Sheet" },
    "bs.period_prefix": { id: "Periode", en: "Period" },
    "bs.posisi_prefix": { id: "Periode", en: "Period" },
    "bs.comp_prefix": { id: "Pembanding", en: "vs." },
    "bs.total_liab_eq": { id: "TOTAL KEWAJIBAN & EKUITAS (PASIVA)", en: "TOTAL LIABILITIES & EQUITY" },
    "bs.footer_system": { id: "Rumus: Total Aktiva (Aset) = Total Kewajiban (Utang) + Total Ekuitas (Modal)", en: "Formula: Total Assets = Total Liabilities + Total Equity" },
    "bs.footer_status": { id: "Status Neraca", en: "Balance Sheet Status" },
    "bs.balanced": { id: "Neraca Seimbang", en: "Balanced" },
    "bs.unbalanced": { id: "Tidak Seimbang", en: "Unbalanced" },
    "bs.footer_total_assets": { id: "Total Aktiva", en: "Total Assets" },
    "bs.footer_total_liabilities_equity": { id: "Total Pasiva", en: "Total Liabilities & Equity" },
    "bs.footer_diff": { id: "Selisih", en: "Difference" },

    // Profit and Loss View Labels
    "pl.title": { id: "Profit and Loss", en: "Profit and Loss" },
    "pl.period_prefix": { id: "Periode", en: "Period" },
    "pl.comp_prefix": { id: "Pembanding", en: "vs." },
    "pl.footer_system": { id: "Rumus: Pendapatan - Beban Pokok - Beban Operasional + Pendapatan Lain = Laba Bersih", en: "Formula: Revenue - Cost of Revenue - Operating Expenses + Other Income = Net Profit" },
    "pl.net_profit_positive": { id: "Laba Bersih Positif", en: "Net Profit Positive" },
    "pl.net_loss_current": { id: "Rugi Bersih Berjalan", en: "Current Net Loss" },
    "pl.gross_profit": { id: "Gross Profit", en: "Gross Profit" },
    "pl.operating_income": { id: "Operating Income", en: "Operating Income" },
    "pl.net_profit": { id: "Net Profit (Loss)", en: "Net Profit (Loss)" },
};

export function getActiveLang() {
    try {
        if (user && user.lang) {
            return user.lang;
        }
        if (user && user.context && user.context.lang) {
            return user.context.lang;
        }
    } catch (e) {}
    return "id_ID";
}

export function translate(key, params = {}) {
    const lang = getActiveLang();
    const isId = !lang || String(lang).toLowerCase().startsWith("id");
    const dict = TRANSLATIONS[key];
    if (!dict) return key;
    let text = isId ? (dict.id || dict.en || key) : (dict.en || dict.id || key);
    if (params) {
        Object.keys(params).forEach(p => {
            text = text.replace(new RegExp(`\\{${p}\\}`, "g"), params[p]);
        });
    }
    return text;
}
