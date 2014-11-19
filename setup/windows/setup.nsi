#####################################################################################
#
# Copyright (c) 2004-TODAY OpenERP S.A. (http://www.openerp.com) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#####################################################################################

!include 'MUI2.nsh'
!include 'FileFunc.nsh'
!include 'LogicLib.nsh'
!include 'Sections.nsh'

!define PUBLISHER 'OpenERP S.A.'

!ifndef VERSION
    !define VERSION '0'
!endif
#!define VERSION "${MAJOR_VERSION}.${MINOR_VERSION}.${REVISION_VERSION}"

!define PRODUCT_NAME "OpenERP Server"
!define DISPLAY_NAME "${PRODUCT_NAME} ${VERSION}"

!define UNINSTALL_REGISTRY_ROOT HKLM
!define UNINSTALL_REGISTRY_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${DISPLAY_NAME}"

!define REGISTRY_KEY "Software\${DISPLAY_NAME}"

!define DEFAULT_POSTGRESQL_HOSTNAME 'localhost'
!define DEFAULT_POSTGRESQL_PORT 5432
!define DEFAULT_POSTGRESQL_USERNAME 'openpg'
!define DEFAULT_POSTGRESQL_PASSWORD 'openpgpwd'

Name '${DISPLAY_NAME}'
Caption "${PRODUCT_NAME} ${VERSION} Setup"
OutFile "openerp-server-setup-${VERSION}.exe"
SetCompressor /final /solid lzma
SetCompress auto
ShowInstDetails show

XPStyle on

InstallDir "$PROGRAMFILES\OpenERP ${VERSION}"
InstallDirRegKey HKCU "${REGISTRY_KEY}" ""

BrandingText '${PRODUCT_NAME} ${VERSION}'

RequestExecutionLevel admin

#VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
#VIAddVersionKey "CompanyName" "${PUBLISHER}"
#VIAddVersionKey "FileDescription" "Installer of ${DISPLAY_NAME}" 
#VIAddVersionKey "LegalCopyright" "${PUBLISHER}"
#VIAddVersionKey "LegalTrademark" "OpenERP is a trademark of ${PUBLISHER}"
#VIAddVersionKey "FileVersion" "${MAJOR_VERSION}.${MINOR_VERSION}.${REVISION_VERSION}"
#VIProductVersion "${MAJOR_VERSION}.${MINOR_VERSION}.${REVISION_VERSION}"

!insertmacro GetParameters
!insertmacro GetOptions

Var Option_AllInOne
Var HasPostgreSQL
Var cmdLineParams

Var TextPostgreSQLHostname
Var TextPostgreSQLPort
Var TextPostgreSQLUsername
Var TextPostgreSQLPassword

Var HWNDPostgreSQLHostname
Var HWNDPostgreSQLPort
Var HWNDPostgreSQLUsername
Var HWNDPostgreSQLPassword

Var MUI_TEMP
Var STARTMENU_FOLDER

!define MUI_ABORTWARNING
!define MUI_ICON ".\install\openerp-icon.ico"

!define MUI_WELCOMEFINISHPAGE_BITMAP ".\install\openerp-intro.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP ".\install\openerp-intro.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP ".\install\openerp-slogan.bmp"
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH
!define MUI_HEADER_TRANSPARENT_TEXT ""

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE ".\LICENSE"
!define MUI_COMPONENTSPAGE_SMALLDESC
!insertmacro MUI_PAGE_DIRECTORY
Page Custom ShowPostgreSQL LeavePostgreSQL

!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM" 
!define MUI_STARTMENUPAGE_REGISTRY_KEY "${REGISTRY_KEY}"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "${DISPLAY_NAME}"

!insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_LINK $(DESC_FinishPage_Link) 
!define MUI_FINISHPAGE_LINK_LOCATION "http://www.openerp.com/contact"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_RESERVEFILE_LANGDLL

!macro CreateInternetShortcut FILENAME URL
	WriteINIStr "${FILENAME}.url" "InternetShortcut" "URL" "${URL}"
!macroend

; English
LangString DESC_FinishPage_Link ${LANG_ENGLISH} "Contact OpenERP for Partnership and/or Support"
LangString WARNING_HostNameIsEmpty ${LANG_ENGLISH} "The hostname for the connection to the PostgreSQL Server is empty"
LangString WARNING_UserNameIsEmpty ${LANG_ENGLISH} "The username for the connection to the PostgreSQL Server is empty"
LangString WARNING_PasswordIsEmpty ${LANG_ENGLISH} "The password for the connection to the PostgreSQL Server is empty"
LangString WARNING_PortIsWrong ${LANG_ENGLISH} "The port for the connexion to the PostgreSQL Server is wrong (default: 5432)"
LangString DESC_PostgreSQLPage ${LANG_ENGLISH} "Configure the information for the PostgreSQL connection"
LangString DESC_PostgreSQL_Hostname ${LANG_ENGLISH} "Hostname"
LangString DESC_PostgreSQL_Port ${LANG_ENGLISH} "Port"
LangString DESC_PostgreSQL_Username ${LANG_ENGLISH} "Username"
LangString DESC_PostgreSQL_Password ${LANG_ENGLISH} "Password"


; French
LangString DESC_FinishPage_Link ${LANG_FRENCH} "Contactez OpenERP pour un Partenariat et/ou du Support"
LangString WARNING_HostNameIsEmpty ${LANG_FRENCH} "L'adresse pour la connection au serveur PostgreSQL est vide"
LangString WARNING_UserNameIsEmpty ${LANG_FRENCH} "Le nom d'utilisateur pour la connection au serveur PostgreSQL est vide"
LangString WARNING_PasswordIsEmpty ${LANG_FRENCH} "Le mot de passe pour la connection au serveur PostgreSQL est vide"
LangString WARNING_PortIsWrong ${LANG_FRENCH} "Le port pour la connection au serveur PostgreSQL est erron? (d?faut: 5432)"
LangString DESC_PostgreSQLPage ${LANG_FRENCH} "Configurez les informations de connection pour le serveur PostgreSQL"
LangString DESC_PostgreSQL_Hostname ${LANG_FRENCH} "H?te"
LangString DESC_PostgreSQL_Port ${LANG_FRENCH} "Port"
LangString DESC_PostgreSQL_Username ${LANG_FRENCH} "Utilisateur"
LangString DESC_PostgreSQL_Password ${LANG_FRENCH} "Mot de passe"

Section -StopService
    nsExec::Exec "net stop openerp-server-7.0"
    sleep 2
SectionEnd

Section OpenERP_Server SectionOpenERP_Server
    SetOutPath '$INSTDIR\server'

    File /r "dist\*"
    File /r "win32\wkhtmltopdf\*"

    SetOutPath "$INSTDIR\service"
    File /r "win32\dist\*"
    File "win32\start.bat"
    File "win32\stop.bat"

    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        ;Create shortcuts
        CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
        !insertmacro CreateInternetShortcut "$SMPROGRAMS\$STARTMENU_FOLDER\OpenERP" "http://localhost:8069/"
    !insertmacro MUI_STARTMENU_WRITE_END


    FileOpen $9 '$INSTDIR\install.log' w
    FileWrite $9 "INSTDIR $INSTDIR$\r$\n"
    FileWrite $9 "Hostname $TextPostgreSQLHostname$\r$\n"
    FileWrite $9 "Port $TextPostgreSQLPort$\r$\n"
    FileWrite $9 "Username $TextPostgreSQLUsername$\r$\n"
    FileWrite $9 "Password $TextPostgreSQLPassword$\r$\n"
    FileClose $9

# If there is a previous install of the OpenERP Server, keep the login/password from the config file
    WriteIniStr "$INSTDIR\server\openerp-server.conf" "options" "db_host" $TextPostgreSQLHostname
    WriteIniStr "$INSTDIR\server\openerp-server.conf" "options" "db_user" $TextPostgreSQLUsername
    WriteIniStr "$INSTDIR\server\openerp-server.conf" "options" "db_password" $TextPostgreSQLPassword
    WriteIniStr "$INSTDIR\server\openerp-server.conf" "options" "db_port" $TextPostgreSQLPort
    WriteIniStr "$INSTDIR\server\openerp-server.conf" "options" "pg_path" "$INSTDIR\PostgreSQL\bin"

    nsExec::Exec '"$INSTDIR\server\openerp-server.exe" --stop-after-init --logfile "$INSTDIR\server\openerp-server.log" -s'
    nsExec::Exec '"$INSTDIR\service\OpenERPServerService.exe" -auto -install'
SectionEnd

Section -RestartServer
    nsExec::Exec "net start openerp-server-7.0"
    sleep 2
SectionEnd

Section -Post
    WriteRegExpandStr HKLM "${UNINSTALL_REGISTRY_KEY}" "UninstallString" "$INSTDIR\server\Uninstall.exe"
    WriteRegExpandStr HKLM "${UNINSTALL_REGISTRY_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "DisplayName" "${DISPLAY_NAME}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "Publisher" "${PUBLISHER}"
;    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "Version" "${VERSION}"
;    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "VersionMajor" "${MAJOR_VERSION}.${MINOR_VERSION}"
;    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "VersionMinor" "${REVISION_VERSION}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "HelpLink" "support@openerp.com"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "HelpTelephone" "+32.81.81.37.00"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "URLInfoAbout" "http://www.openerp.com"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "Contact" "sales@openerp.com"
    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "NoModify" "1"
    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "NoRepair" "1"
    WriteUninstaller "$INSTDIR\server\Uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Stop the NT Service
    nsExec::Exec "net stop openerp-server-7.0"
    sleep 2

    ; Uninstall the OpenERP Service
    nsExec::Exec '"$INSTDIR\..\service\OpenERPServerService.exe" -remove'
    sleep 2

    Rmdir /r "$INSTDIR\service"
    Rmdir /r "$INSTDIR\server"

    !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP

    Delete "$SMPROGRAMS\$MUI_TEMP\OpenERP.url"
    ;
    ;Delete empty start menu parent diretories
    StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"
 
    startMenuDeleteLoop:
        ClearErrors
        RMDir $MUI_TEMP
        GetFullPathName $MUI_TEMP "$MUI_TEMP\.."

        IfErrors startMenuDeleteLoopDone

        StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop

    startMenuDeleteLoopDone:

    ; Clean the Registry
    DeleteRegKey HKLM "${UNINSTALL_REGISTRY_KEY}"
SectionEnd

Function .onInit
    Push $R0

    ${GetParameters} $cmdLineParams
    ClearErrors

    Pop $R0

    StrCpy $Option_AllInOne 0
    StrCpy $HasPostgreSQL 0

    StrCpy $TextPostgreSQLHostname ${DEFAULT_POSTGRESQL_HOSTNAME}
    StrCpy $TextPostgreSQLPort ${DEFAULT_POSTGRESQL_PORT}
    StrCpy $TextPostgreSQLUsername ${DEFAULT_POSTGRESQL_USERNAME}
    StrCpy $TextPostgreSQLPassword ${DEFAULT_POSTGRESQL_PASSWORD}

    Push $R0
    ${GetOptions} $cmdLineParams '/allinone' $R0
    IfErrors +2 0
    StrCpy $Option_AllInOne 1
    Pop $R0

    StrCmp $Option_AllInOne 1 AllInOneMode
    StrCmp $Option_AllInOne 0 NoAllInOneMode

    AllInOneMode:
        MessageBox MB_OK|MB_ICONINFORMATION "All In One"

    NoAllInOneMode:
    
    !insertmacro MUI_LANGDLL_DISPLAY

    ClearErrors
    EnumRegKey $0 HKLM "SOFTWARE\PostgreSQL\Installations" 0
    IfErrors DoInstallPostgreSQL 0
    StrCmp $0 "" DoInstallPostgreSQL
    StrCpy $HasPostgreSQL 1

    DoInstallPostgreSQL:
FunctionEnd

Function PostgreSQLOnBack
FunctionEnd

Function ShowPostgreSQL
    SectionGetFlags ${SectionOpenERP_Server} $0
    IntOp $0 $0 & ${SF_SELECTED}
    IntCmp $0 ${SF_SELECTED} LaunchPostgreSQLConfiguration
    Abort
    LaunchPostgreSQLConfiguration:

    nsDialogs::Create /NOUNLOAD 1018
    Pop $0

    ${If} $0 == error
        Abort
    ${EndIf}

    GetFunctionAddress $0 PostgreSQLOnBack
    nsDialogs::OnBack $0

    ${NSD_CreateLabel} 0 0 100% 10u $(DESC_PostgreSQLPage)
    Pop $0

    ${NSD_CreateLabel} 0 45 60u 12u $(DESC_PostgreSQL_Hostname)
    Pop $0
    ${NSD_CreateText} 100 45 150u 12u $TextPostgreSQLHostname
    Pop $HWNDPostgreSQLHostname

    ${NSD_CreateLabel} 0 75 60u 12u $(DESC_PostgreSQL_Port)
    Pop $0
    ${NSD_CreateNumber} 100 75 150u 12u $TextPostgreSQLPort
    Pop $HWNDPostgreSQLPort
    ${NSD_CreateLabel} 0 105 60u 12u $(DESC_PostgreSQL_Username)
    Pop $0
    ${NSD_CreateText} 100 105 150u 12u $TextPostgreSQLUsername
    Pop $HWNDPostgreSQLUsername
    ${NSD_CreateLabel} 0 135 60u 12u $(DESC_PostgreSQL_Password)
    Pop $0
    ${NSD_CreateText} 100 135 150u 12u $TextPostgreSQLPassword
    Pop $HWNDPostgreSQLPassword

    nsDialogs::Show
FunctionEnd

Function LeavePostgreSQL
    # Before to leave the PostgreSQL configuration screen, we check the values
    # from the inputs, to be sure we have the right values

    ${NSD_GetText} $HWNDPostgreSQLHostname $TextPostgreSQLHostname
    ${NSD_GetText} $HWNDPostgreSQLPort $TextPostgreSQLPort
    ${NSD_GetText} $HWNDPostgreSQLUsername $TextPostgreSQLUsername
    ${NSD_GetText} $HWNDPostgreSQLPassword $TextPostgreSQLPassword

    StrLen $1 $TextPostgreSQLHostname
    ${If} $1 == 0
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_HostNameIsEmpty)
        Abort
    ${EndIf}

    ${If} $TextPostgreSQLPort <= 0
    ${OrIf} $TextPostgreSQLPort > 65535
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_PortIsWrong)
        Abort
    ${EndIf}

    StrLen $1 $TextPostgreSQLUsername
    ${If} $1 == 0
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_UserNameIsEmpty)
        Abort
    ${EndIf}

    StrLen $1 $TextPostgreSQLPassword
    ${If} $1 == 0
        MessageBox MB_ICONEXCLAMATION|MB_OK $(WARNING_PasswordIsEmpty)
        Abort
    ${EndIf}
FunctionEnd

