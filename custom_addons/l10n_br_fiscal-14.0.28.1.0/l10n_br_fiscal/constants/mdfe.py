# Copyright (C) 2020  KMEE Informática LTDA
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

SIT_MANIF_PENDENTE = ("pendente", "Pendente")
SIT_MANIF_CIENTE = ("ciente", "Ciente da Operação")
SIT_MANIF_CONFIRMADO = ("confirmado", "Confirmada operação")
SIT_MANIF_DESCONHECIDO = ("desconhecido", "Desconhecimento")
SIT_MANIF_NAO_REALIZADO = ("nao_realizado", "Não realizado")

SITUACAO_MANIFESTACAO = [
    SIT_MANIF_PENDENTE,
    SIT_MANIF_CIENTE,
    SIT_MANIF_CONFIRMADO,
    SIT_MANIF_DESCONHECIDO,
    SIT_MANIF_NAO_REALIZADO,
]

SIT_NFE_AUTORIZADA = ("1", "Autorizada")
SIT_NFE_CANCELADA = ("2", "Cancelada")
SIT_NFE_DENEGADA = ("3", "Denegada")

SITUACAO_NFE = [SIT_NFE_AUTORIZADA, SIT_NFE_CANCELADA, SIT_NFE_DENEGADA]

OP_TYPE_ENTRADA = ("0", "Entrada")
OP_TYPE_SAIDA = ("1", "Saída")

OPERATION_TYPE = [OP_TYPE_ENTRADA, OP_TYPE_SAIDA]
