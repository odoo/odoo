type TopbarProps = {
  title: string;
};

export function Topbar({ title }: TopbarProps) {
  return (
    <header
      style={{
        height: 56,
        borderBottom: "1px solid var(--o-color-border)",
        background: "var(--o-color-surface)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        position: "sticky",
        top: 0,
        zIndex: 20
      }}
    >
      <strong style={{ color: "var(--o-color-primary)" }}>{title}</strong>
      <span style={{ color: "var(--o-color-muted)", fontSize: 13 }}>Dummy Odoo Frontend</span>
    </header>
  );
}
