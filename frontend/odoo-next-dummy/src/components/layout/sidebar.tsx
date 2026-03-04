"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/processos", label: "Processos" },
  { href: "/documento-dfd/1", label: "Documento DFD" }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: 232,
        borderRight: "1px solid var(--o-color-border)",
        background: "var(--o-color-surface)",
        padding: 14
      }}
    >
      <div style={{ padding: "8px 10px", fontSize: 13, color: "var(--o-color-muted)" }}>
        Navegacao
      </div>
      <nav style={{ display: "grid", gap: 6 }}>
        {links.map((link) => {
          const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
          return (
            <Link
              key={link.href}
              href={link.href}
              style={{
                display: "block",
                padding: "10px 12px",
                borderRadius: 8,
                fontWeight: isActive ? 600 : 500,
                color: isActive ? "white" : "var(--o-color-text)",
                background: isActive ? "var(--o-color-primary)" : "transparent",
                transition: "120ms ease"
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
