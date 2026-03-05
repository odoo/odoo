"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { govSuiteList } from "@/lib/gov-suite";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/gov", label: "Gov Suite" },
  { href: "/processos", label: "Processos (legacy)" },
  { href: "/documento-dfd/1", label: "Documento DFD (legacy)" }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar-panel">
      <div className="sidebar-brand">Plataforma GRP</div>
      <div className="sidebar-label">Navegacao</div>
      <nav style={{ display: "grid", gap: 6 }}>
        {links.map((link) => {
          const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`nav-link${isActive ? " active" : ""}`}
            >
              {link.label}
            </Link>
          );
        })}
        <div className="sidebar-label">Modulos GOV</div>
        {govSuiteList.map((suite) => {
          const isActive = pathname.startsWith(suite.path);
          return (
            <Link
              key={suite.key}
              href={suite.path}
              className={`nav-link${isActive ? " active" : ""}`}
              style={{ fontSize: 13 }}
            >
              {suite.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
