import Link from "next/link";
import { Card } from "@/components/ui/card";
import { govSuiteList } from "@/lib/gov-suite";

export default function GovHomePage() {
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card title="Gov Suite">
        <p style={{ marginTop: 0, color: "var(--o-color-muted)" }}>
          Base inicial para os modulos gov do seu Odoo, com BFF e UI padrao.
        </p>
        <div style={{ display: "grid", gap: 8 }}>
          {govSuiteList.map((suite) => (
            <Link key={suite.key} href={suite.path} style={{ color: "var(--o-color-primary)", fontWeight: 600 }}>
              Abrir {suite.label}
            </Link>
          ))}
        </div>
      </Card>
    </div>
  );
}
