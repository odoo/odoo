import { StatusState } from "@/components/ui/status-state";

export default function Loading() {
  return <StatusState kind="loading" message="Carregando pagina..." />;
}
