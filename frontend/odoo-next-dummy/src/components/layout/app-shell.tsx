"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { getGovSuiteByPath } from "@/lib/gov-suite";

const titleByPath: Record<string, string> = {
  "/": "Dashboard",
  "/gov": "Gov Suite",
  "/processos": "Processos",
  "/documento-dfd": "Documento DFD"
};

function getTitle(pathname: string): string {
  const govSuite = getGovSuiteByPath(pathname);
  if (govSuite) {
    return govSuite.label;
  }
  if (pathname.startsWith("/gov")) {
    return titleByPath["/gov"];
  }
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
    <div className="app-shell">
      <Topbar title={getTitle(pathname)} />
      <div className="app-main-grid">
        <Sidebar />
        <main className="app-main-content">{children}</main>
      </div>
    </div>
  );
}
