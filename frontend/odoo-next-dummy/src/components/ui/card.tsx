import { ReactNode } from "react";

type CardProps = {
  title: string;
  value?: string | number;
  children?: ReactNode;
};

export function Card({ title, value, children }: CardProps) {
  return (
    <section className="surface-card">
      <div className="surface-title">{title}</div>
      {value !== undefined && <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>{value}</div>}
      {children}
    </section>
  );
}
