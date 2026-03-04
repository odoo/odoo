import { ReactNode } from "react";

type Column<T> = {
  key: keyof T;
  label: string;
  render?: (row: T) => ReactNode;
};

type DataTableProps<T extends { id: number }> = {
  rows: T[];
  columns: Array<Column<T>>;
};

export function DataTable<T extends { id: number }>({ rows, columns }: DataTableProps<T>) {
  return (
    <div
      style={{
        border: "1px solid var(--o-color-border)",
        borderRadius: "var(--o-radius)",
        overflow: "hidden",
        background: "var(--o-color-surface)"
      }}
    >
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead style={{ background: "#f7f7fb" }}>
          <tr>
            {columns.map((column) => (
              <th
                key={String(column.key)}
                style={{
                  textAlign: "left",
                  fontSize: 13,
                  color: "var(--o-color-muted)",
                  padding: "10px 12px",
                  borderBottom: "1px solid var(--o-color-border)"
                }}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((column) => (
                <td
                  key={`${row.id}-${String(column.key)}`}
                  style={{ padding: "12px", borderBottom: "1px solid var(--o-color-border)", fontSize: 14 }}
                >
                  {column.render ? column.render(row) : String(row[column.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
