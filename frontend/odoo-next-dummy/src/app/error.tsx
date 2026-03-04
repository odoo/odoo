"use client";

import { StatusState } from "@/components/ui/status-state";

export default function ErrorPage() {
  return <StatusState kind="error" message="Falha ao carregar esta pagina." />;
}
