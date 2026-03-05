type TopbarProps = {
  title: string;
};

export function Topbar({ title }: TopbarProps) {
  return (
    <header className="app-topbar">
      <div style={{ display: "grid", gap: 2 }}>
        <small style={{ color: "var(--o-color-muted)", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          Gov Suite
        </small>
        <strong style={{ color: "var(--o-color-primary-700)", fontSize: 18 }}>{title}</strong>
      </div>
      <span style={{ color: "var(--o-color-muted)", fontSize: 13 }}>GRP Frontend</span>
    </header>
  );
}
