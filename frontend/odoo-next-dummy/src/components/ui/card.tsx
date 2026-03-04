import { ReactNode } from "react";

type CardProps = {
  title: string;
  value?: string | number;
  children?: ReactNode;
};

export function Card({ title, value, children }: CardProps) {
  return (
    <section
      style={{
        background: "var(--o-color-surface)",
        border: "1px solid var(--o-color-border)",
        borderRadius: "var(--o-radius)",
        boxShadow: "var(--o-shadow-soft)",
        padding: 16
      }}
    >
      <div style={{ color: "var(--o-color-muted)", fontSize: 13, marginBottom: 8 }}>{title}</div>
      {value !== undefined && <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>{value}</div>}
      {children}
    </section>
  );
}
