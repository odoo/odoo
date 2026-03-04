"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import { StatusState } from "@/components/ui/status-state";

type Processo = {
  id: number;
  nome: string;
  criadoEm: string;
  atualizadoEm: string;
};

type ProcessosResponse = {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  items: Processo[];
};

export function ProcessosView() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ProcessosResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`/api/processos?page=${page}&pageSize=10`);
        if (!response.ok) {
          const payload = await response.json();
          throw new Error(payload.error ?? "Erro ao carregar processos");
        }
        const payload = (await response.json()) as ProcessosResponse;
        setData(payload);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro inesperado");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [page]);

  if (loading) {
    return <StatusState kind="loading" message="Buscando processos..." />;
  }
  if (error) {
    return <StatusState kind="error" message={error} />;
  }
  if (!data || data.items.length === 0) {
    return <StatusState kind="empty" message="Nenhum processo retornado pela API." />;
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card title={`Processos (${data.total})`}>
        <DataTable
          rows={data.items}
          columns={[
            { key: "id", label: "ID" },
            {
              key: "nome",
              label: "Nome",
              render: (row) => <Link href={`/documento-dfd/${row.id}`}>{row.nome}</Link>
            },
            { key: "criadoEm", label: "Criado em" },
            { key: "atualizadoEm", label: "Atualizado em" }
          ]}
        />
      </Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button
          type="button"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          style={{ padding: "8px 12px" }}
        >
          Anterior
        </button>
        <span style={{ color: "var(--o-color-muted)" }}>
          Pagina {data.page} de {data.totalPages}
        </span>
        <button
          type="button"
          onClick={() => setPage((p) => Math.min(data.totalPages, p + 1))}
          disabled={page >= data.totalPages}
          style={{ padding: "8px 12px" }}
        >
          Proxima
        </button>
      </div>
    </div>
  );
}
