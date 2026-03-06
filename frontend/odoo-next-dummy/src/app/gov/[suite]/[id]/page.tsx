import { GovDetailView } from "@/components/gov/gov-detail-view";
import { StatusState } from "@/components/ui/status-state";
import { getGovSuiteBySlug } from "@/lib/gov-suite";

type GovDetailPageProps = {
  params: Promise<{ suite: string; id: string }>;
};

export default async function GovDetailPage({ params }: GovDetailPageProps) {
  const resolved = await params;
  const suite = getGovSuiteBySlug(resolved.suite);
  const id = Number.parseInt(resolved.id, 10);

  if (!suite) {
    return <StatusState kind="error" message={`Suite gov/${resolved.suite} nao encontrada.`} />;
  }
  if (Number.isNaN(id) || id <= 0) {
    return <StatusState kind="error" message="ID invalido." />;
  }

  return <GovDetailView suiteKey={suite.key} id={id} />;
}
