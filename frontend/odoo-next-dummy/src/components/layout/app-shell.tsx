"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

const titleByPath: Record<string, string> = {
  "/": "Dashboard",
  "/processos": "Processos",
  "/documento-dfd": "Documento DFD"
};

function getTitle(pathname: string): string {
  if (pathname.startsWith("/documento-dfd")) {
    return titleByPath["/documento-dfd"];
  }
  return titleByPath[pathname] ?? "Odoo Frontend";
}

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();

  return (
    <div style={{ minHeight: "100dvh", display: "grid", gridTemplateRows: "56px 1fr" }}>
      <Topbar title={getTitle(pathname)} />
      <div style={{ display: "grid", gridTemplateColumns: "232px 1fr", minHeight: 0 }}>
        <Sidebar />
        <main style={{ padding: 20 }}>{children}</main>
      </div>
    </div>
  );
}
