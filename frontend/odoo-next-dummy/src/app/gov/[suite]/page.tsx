import { GovListView } from "@/components/gov/gov-list-view";
import { StatusState } from "@/components/ui/status-state";
import { getGovSuiteBySlug } from "@/lib/gov-suite";

type GovSuitePageProps = {
  params: Promise<{ suite: string }>;
};

export default async function GovSuitePage({ params }: GovSuitePageProps) {
  const resolved = await params;
  const suite = getGovSuiteBySlug(resolved.suite);

  if (!suite) {
    return <StatusState kind="error" message={`Suite gov/${resolved.suite} nao encontrada.`} />;
  }

  return <GovListView suite={suite} />;
}
