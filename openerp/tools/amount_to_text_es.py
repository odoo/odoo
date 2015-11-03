# -*- coding: utf-8 -*-
_n1 = ( "un","dos","tres","cuatro","cinco","seis","siete","ocho",
        "nueve","diez","once","doce","trece","catorce","quince",
        "dieciseis","diecisiete","dieciocho","diecinueve","veinte")

_n11 =( "un","dos","tres","cuatro","cinco","seis","siete","ocho","nueve")

_n2 = ( "dieci","veinti","treinta","cuarenta","cincuenta","sesenta",
        "setenta","ochenta","noventa")

_n3 = ( "ciento","dosc","tresc","cuatroc","quin","seisc",
        "setec","ochoc","novec")

def numerals(nNumero):
    # Nos aseguramos del tipo de <nNumero>
    # se podría adaptar para usar otros tipos (pe: float)
    nNumero = long(nNumero)

    if nNumero<0:       cRes = "menos "+_numerals(-nNumero)
    elif nNumero==0:    cRes = "cero"
    else:               cRes = _numerals(nNumero)

    # Excepciones a considerar
    if nNumero%10 == 1 and nNumero%100!=11:
        cRes += "o"

    return cRes


# Funcion auxiliar recursiva
def _numerals(n):

    # Localizar los billones    
    prim,resto = divmod(n,10L**12)
    if prim!=0:
        if prim==1:     cRes = "un billon"
        else:           cRes = _numerals(prim,0)+" billones" # Billones es masculino

        if resto!=0:    cRes += " "+_numerals(resto)

    else:
    # Localizar millones
        prim,resto = divmod(n,10**6)
        if prim!=0:
            if prim==1: cRes = "un millon"
            else:       cRes = _numerals(prim)+" millones" # Millones es masculino

            if resto!=0: cRes += " " + _numerals(resto)

        else:
    # Localizar los miles
            prim,resto = divmod(n,10**3)
            if prim!=0:
                if prim==1: cRes="mil"
                else:       cRes=_numerals(prim)+" mil"

                if resto!=0: cRes += " " + _numerals(resto)

            else:
    # Localizar los cientos
                prim,resto=divmod(n,100)
                if prim!=0:
                    if prim==1:
                        if resto==0:        cRes="cien"
                        else:               cRes="ciento"
                    else:
                        cRes=_n3[prim-1]
                        cRes+="ientos"

                    if resto!=0:  cRes+=" "+_numerals(resto)

                else:
    # Localizar las decenas
                    if n==1:              cRes="un"
                    elif n<=20:                         cRes=_n1[n-1]
                    else:
                        prim,resto=divmod(n,10)
                        cRes=_n2[prim-1]
                        if resto!=0:
                            if prim==2:                 cRes+=_n11[resto-1]
                            else:                       cRes+=" y "+_n1[resto-1]

                            if resto==1:  cRes+=""
    return cRes
