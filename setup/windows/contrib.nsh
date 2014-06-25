# Source: http://nsis.sourceforge.net/CharToASCII
!include LogicLib.nsh

!ifndef CHAR_TO_ASCII_NSH

!define CharToASCII "!insertmacro CharToASCII" 
 
!macro CharToASCII AsciiCode Character
  Push "${Character}"
  Call CharToASCII
  Pop "${AsciiCode}"
!macroend
 
Function CharToASCII
  Exch $0 ; given character
  Push $1 ; current character
  Push $2 ; current Ascii Code   
 
  StrCpy $2 1 ; right from start
Loop:
  IntFmt $1 %c $2 ; Get character from current ASCII code
  ${If} $1 S== $0 ; case sensitive string comparison
     StrCpy $0 $2
     Goto Done
  ${EndIf}
  IntOp $2 $2 + 1
  StrCmp $2 255 0 Loop ; ascii from 1 to 255
  StrCpy $0 0 ; ASCII code wasn't found -> return 0
Done:         
  Pop $2
  Pop $1
  Exch $0
FunctionEnd

!endif ; CHAR_TO_ASCII_NSH

# Source: http://nsis.sourceforge.net/Base64
!ifndef BASE64_NSH
!define BASE64_NSH
 
!define BASE64_ENCODINGTABLE "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
!define BASE64_ENCODINGTABLEURL "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
 
!define BASE64_PADDING "="
 
VAR   OCTETVALUE
VAR  BASE64TEMP
 
!define Base64_Encode "!insertmacro Base64_Encode"
!define Base64_URLEncode "!insertmacro Base64_URLEncode"
 
!macro  Base64_Encode _cleartext
  push $R0
  push $R1
  push $R2
  push $0
  push $1
  push $2
  push $3
  push $4
  push $5
  push $6
  push $7
  push `${_cleartext}`
  push `${BASE64_ENCODINGTABLE}`
  Call Base64_Encode
  Pop $BASE64TEMP
  Pop $7
  Pop $6
  Pop $5
  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Pop $0
  pop $R2
  pop $R1
  pop $R0
  Push $BASE64TEMP
!macroend
 
!macro  Base64_URLEncode _cleartext
  push $R0
  push $R1
  push $R2
  push $0
  push $1
  push $2
  push $3
  push $4
  push $5
  push $6
  push $7
  push `${_cleartext}`
  push `${BASE64_ENCODINGTABLEURL}`
  Call Base64_Encode
  Pop $BASE64TEMP
  Pop $7
  Pop $6
  Pop $5
  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Pop $0
  pop $R2
  pop $R1
  pop $R0
  Push $BASE64TEMP
!macroend
 
Function Base64_Encode
  pop $R2 ; Encoding table
  pop $R0 ; Clear Text
  StrCpy "$R1" "" # The result
 
  StrLen $1 "$R0"
  StrCpy $0 0
 
  ${WHILE} $0 < $1
    # Copy 3 characters, and for each character push their value.
    StrCpy $OCTETVALUE 0
 
    StrCpy $5 $0
    StrCpy $4 "$R0" 1 $5
    ${CharToASCII} $4 "$4"
 
    IntOp $OCTETVALUE $4 << 16
 
    IntOp $5 $5 + 1
    ${IF} $5 < $1
      StrCpy $4 "$R0" 1 $5
      ${CharToASCII} $4 "$4"
 
      IntOp $4 $4 << 8
      IntOp $OCTETVALUE $OCTETVALUE + $4
 
      IntOp $5 $5 + 1
      ${IF} $5 < $1
        StrCpy $4 "$R0" 1 $5
        ${CharToASCII} $4 "$4"
 
        IntOp $OCTETVALUE $OCTETVALUE + $4
      ${ENDIF}
    ${ENDIF}
 
    # Now take the 4 indexes from the encoding table, based on 6bits each of the octet's value.
    IntOp $4 $OCTETVALUE >> 18
    IntOp $4 $4 & 63
    StrCpy $5   "$R2" 1 $4
    StrCpy $R1  "$R1$5"
 
    IntOp $4 $OCTETVALUE >> 12
    IntOp $4 $4 & 63
    StrCpy $5   "$R2" 1 $4
    StrCpy $R1  "$R1$5"
 
    StrCpy $6 $0
    StrCpy $7 2
 
    IntOp $6 $6 + 1
    ${IF} $6 < $1
      IntOp $4 $OCTETVALUE >> 6
      IntOp $4 $4 & 63
      StrCpy $5   "$R2" 1 $4
      StrCpy $R1  "$R1$5"
      IntOp $7 $7 - 1
    ${ENDIF}
 
    IntOp $6 $6 + 1
    ${IF} $6 < $1
      IntOp $4 $OCTETVALUE & 63
      StrCpy $5   "$R2" 1 $4
      StrCpy $R1  "$R1$5"
      IntOp $7 $7 - 1
    ${ENDIF}
 
    # If there is any padding required, we now write that here.
    ${IF} $7 > 0
      ${WHILE} $7 > 0
        StrCpy $R1 "$R1${BASE64_PADDING}"
        IntOp $7 $7 - 1
      ${ENDWHILE}
    ${ENDIF}
 
    IntOp $0 $0 + 3
  ${ENDWHILE}
 
  Push "$R1"
FunctionEnd
 
 
!define Base64_Decode "!insertmacro Base64_Decode"
!define Base64_URLDecode "!insertmacro Base64_URLDecode"
 
!macro  Base64_Decode _encodedtext
  push `${_encodedtext}`
  push `${BASE64_ENCODINGTABLE}`
  Call Base64_Decode
!macroend
 
!macro  Base64_URLDecode _encodedtext
  push `${_encodedtext}`
  push `${BASE64_ENCODINGTABLEURL}`
  Call Base64_Decode
!macroend
 
Function base64_Decode
            ; Stack: strBase64table strEncoded
  Push $9   ; Stack: $9 strBase64table strEncoded   ; $9 = strDecoded
  Exch 2    ; Stack: strEncoded strBase64table $9
  Exch      ; Stack: strBase64table strEncoded $9
  Exch $0   ; Stack: $0 strEncoded $9               ; $0 = strBase64table
  Exch      ; Stack: strEncoded $0 $9
  Exch $1   ; Stack: $1 $0 $9                       ; $1 = strEncoded
 
  Push $2   ; strBase64table.length
  Push $3   ; strEncoded.length
  Push $4   ; strBase64table.counter
  Push $5   ; strEncoded.counter
  Push $6   ; strBase64table.char
  Push $7   ; strEncoded.char
 
  Push $R0  ; 6bit-group.counter
  Push $R1  ; 6bit-group.a
  Push $R2  ; 6bit-group.b
  Push $R3  ; 6bit-group.c
  Push $R4  ; 6bit-group.d
 
  Push $R5  ; bit-group.tempVar.a
  Push $R6  ; bit-group.tempVar.b
 
  Push $R7  ; 8bit-group.A
  Push $R8  ; 8bit-group.B
  Push $R9  ; 8bit-group.C
 
  StrCpy $9 "" ; Result string
 
  StrLen $2 "$0" ; Get the length of the base64 table into $2
  StrLen $3 "$1" ; Get the length of the encoded text into $3
  IntOp $3 $3 - 1 ; Subtract one as the StrCpy offset is zero-based
 
  StrCpy $R0 4 ; Initialize the 6bit-group.counter
 
  ${ForEach} $5 0 $3 + 1 ; Loop over the encoded string
    StrCpy $7 $1 1 $5 ; Grab the character at the loop counter's index
 
    ${If} $7 == "${BASE64_PADDING}" ; If it's the padding char
      Push 0 ; Push value 0 (no impact on decoded string)
    ${Else} ; Otherwise
      ${ForEach} $4 0 $2 + 1 ; Loop over the base64 lookup table
        StrCpy $6 $0 1 $4 ; Grab the character at this loop counter's index
        ${If} $6 S== $7 ; If that character matches the encoded string character
          ${ExitFor} ; Exit this loop early
        ${EndIf}
      ${Next}
      Push $4 ; Push the lookup's index to the stack
    ${EndIf}
 
    IntOp $R0 $R0 - 1 ; Decrease the 6bit-group counter
 
    ${If} $R0 = 0 ; If that counter reaches zero
      ; Pop the index values off the stack to variables
      Pop $R4
      Pop $R3
      Pop $R2
      Pop $R1
 
      ; The way the base64 decoding works is like this...
      ; Normal ASCII has 8 bits, base64 has 6 bits.
      ; Those 8 bits need to be presented as 6 bits somehow
      ; Turns out you can easily do that by taking their common multiple: 24
      ; This results in 3 8bit characters per each 4 6bit characters:
      ; AAAAAAAA BBBBBBBB CCCCCCCC
      ; aaaaaabb bbbbcccc ccdddddd
 
      ; So to go back to AAAAAAAA, you need:
      ;   aaaaaa shifted two bits to the left
      ;   the two left-most bits of bbbbbb,
      ;     which you can do by shifting it four bits to the right
      IntOp $R5 $R1 << 2
      IntOp $R6 $R2 >> 4
      IntOp $R5 $R5 | $R6
      IntFmt $R7 "%c" $R5 ; IntFmt turns the resulting 8bit value to a character
 
      ; For BBBBBBBB, you need:
      ;   the four least significant bits of bbbbbb
      ;     which you can get by binary OR'ing with 2^4-1 = 15
      ;   the four most significant bits of cccccc
      ;     which you can get by just shifting it two bits to the right
      IntOp $R5 $R2 & 15
      InTop $R5 $R5 << 4
      IntOp $R6 $R3 >> 2
      IntOp $R5 $R5 | $R6
      IntFmt $R8 "%c" $R5
 
      ; For CCCCCCCC, the procedure is entirely similar.
      IntOp $R5 $R3 & 3
      IntOp $R5 $R5 << 6
      IntOp $R5 $R5 | $R4
      IntFmt $R9 "%c" $R5
 
      StrCpy $9 "$9$R7$R8$R9" ; Tack it all onto the result
      StrCpy $R0 4 ; Reset the 6bit-group counter
    ${EndIf}
  ${Next}
 
  ; Done.  Now let's restore the user's variables
  Pop $R9
  Pop $R8
  Pop $R7
  Pop $R6
  Pop $R5
  Pop $R4
  Pop $R3
  Pop $R2
  Pop $R1
  Pop $R0
  Pop $7
  Pop $6
  Pop $5
  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Pop $0
  Exch $9   ; Stack: strDecoded
FunctionEnd
!endif ;BASE64_NSH