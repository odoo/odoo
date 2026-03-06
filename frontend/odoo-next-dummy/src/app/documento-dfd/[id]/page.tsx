import { DocumentoDfdView } from "@/components/documento/documento-dfd-view";

type DocumentoPageProps = {
  params: Promise<{ id: string }>;
};

export default async function DocumentoPage({ params }: DocumentoPageProps) {
  const resolvedParams = await params;
  const id = Number.parseInt(resolvedParams.id, 10);

  return <DocumentoDfdView id={Number.isNaN(id) ? 0 : id} />;
}
