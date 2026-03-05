"use client";

import { ReactNode, useState } from "react";

type TabItem = {
  id: string;
  label: string;
  content: ReactNode;
};

type TabsProps = {
  items: TabItem[];
};

export function Tabs({ items }: TabsProps) {
  const [active, setActive] = useState(items[0]?.id ?? "");
  const current = items.find((item) => item.id === active);

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        {items.map((item) => {
          const isActive = item.id === active;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => setActive(item.id)}
              style={{
                border: "1px solid var(--o-color-border)",
                borderRadius: 8,
                background: isActive
                  ? "linear-gradient(90deg, var(--o-color-primary), var(--o-color-primary-700))"
                  : "var(--o-color-surface)",
                color: isActive ? "white" : "var(--o-color-text)",
                padding: "8px 12px",
                cursor: "pointer"
              }}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      <div>{current?.content}</div>
    </div>
  );
}
