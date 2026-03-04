import type { Metadata } from "next";
import { ReactNode } from "react";
import { AppShell } from "@/components/layout/app-shell";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: "Odoo Next Dummy",
  description: "Frontend Next.js com BFF para Odoo"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
