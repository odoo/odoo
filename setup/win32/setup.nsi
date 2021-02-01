# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO: Avoid to uninstall the database
# TODO: We can update the server or the clients without to uninstall the all-in-one
# TODO: Add startmenu handling (link to localhost + uninstall)

!include 'MUI2.nsh'
!include 'FileFunc.nsh'
!include 'LogicLib.nsh'
!include 'Sections.nsh'
!include 'x64.nsh'

!macro IfKeyExists ROOT MAIN_KEY KEY
    # This macro comes from http://nsis.sourceforge.net/Check_for_a_Registry_Key
    Push $R0
    Push $R1
    Push $R2
 
    # XXX bug if ${ROOT}, ${MAIN_KEY} or ${KEY} use $R0 or $R1
 
    StrCpy $R1 "0" # loop index
    StrCpy $R2 "0" # not found
 
    ${Do}
        EnumRegKey $R0 ${ROOT} "${MAIN_KEY}" "$R1"
        ${If} $R0 == "${KEY}"
            StrCpy $R2 "1" # found
            ${Break}
        ${EndIf}
        IntOp $R1 $R1 + 1
    ${LoopWhile} $R0 != ""
 
    ClearErrors
 
    Exch 2
    Pop $R0
    Pop $R1
    Exch $R2
!macroend

!define PUBLISHER 'Odoo S.A.'

!ifndef MAJOR_VERSION
    !define MAJOR_VERSION '12'
!endif

!ifndef MINOR_VERSION
    !define MINOR_VERSION '0'
!endif

!ifndef REVISION_VERSION
    !define REVISION_VERSION 'alpha1'
!endif

!ifndef VERSION
    !define VERSION "0"
#!define VERSION "${MAJOR_VERSION}.${MINOR_VERSION}-r${REVISION_VERSION}"
!endif

!define PRODUCT_NAME "Odoo"
!define DISPLAY_NAME "${PRODUCT_NAME} ${MAJOR_VERSION}.${MINOR_VERSION}"

!define REGISTRY_ROOT HKLM
!define UNINSTALL_BASE_REGISTRY_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall"
!define UNINSTALL_REGISTRY_KEY "${UNINSTALL_BASE_REGISTRY_KEY}\${DISPLAY_NAME}"

!define UNINSTALL_REGISTRY_KEY_SERVER "${UNINSTALL_BASE_REGISTRY_KEY}\Odoo Server ${VERSION}"

!define REGISTRY_KEY "Software\${DISPLAY_NAME}"

!define DEFAULT_POSTGRESQL_HOSTNAME 'localhost'
!define DEFAULT_POSTGRESQL_PORT 5432
!define DEFAULT_POSTGRESQL_USERNAME 'openpg'
!define DEFAULT_POSTGRESQL_PASSWORD 'openpgpwd'

Name '${DISPLAY_NAME}'
Caption "${PRODUCT_NAME} ${VERSION} Setup"
OutFile "openerp-allinone-setup-${VERSION}.exe"
SetCompressor /FINAL lzma
#SetCompress auto
ShowInstDetails show

#XPStyle on

InstallDir "$PROGRAMFILES\Odoo ${VERSION}"
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

!define STATIC_PATH "static"
!define PIXMAPS_PATH "${STATIC_PATH}\pixmaps"
!define POSTGRESQL_EXE_FILENAME "postgresql-9.5.8-1-windows.exe"
!define POSTGRESQL_EXE "${STATIC_PATH}\${POSTGRESQL_EXE_FILENAME}"

!define MUI_ABORTWARNING
!define MUI_ICON "${PIXMAPS_PATH}\openerp-icon.ico"

!define MUI_WELCOMEFINISHPAGE_BITMAP "${PIXMAPS_PATH}\openerp-intro.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${PIXMAPS_PATH}\openerp-intro.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "${PIXMAPS_PATH}\openerp-slogan.bmp"
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH
!define MUI_HEADER_TRANSPARENT_TEXT ""

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${STATIC_PATH}\doc\LICENSE"
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE ComponentLeave
!insertmacro MUI_PAGE_COMPONENTS
Page Custom ShowPostgreSQL LeavePostgreSQL
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_CHECKED
!define MUI_FINISHPAGE_RUN_TEXT "$(DESC_FinishPageText)"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
!define MUI_FINISHPAGE_LINK $(DESC_FinishPage_Link) 
!define MUI_FINISHPAGE_LINK_LOCATION "https://www.odoo.com/page/contactus"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_RESERVEFILE_LANGDLL

; English
LangString DESC_OpenERP_Server ${LANG_ENGLISH} "Install the Odoo Server with all the Odoo standard modules."
LangString DESC_PostgreSQL ${LANG_ENGLISH} "Install the PostgreSQL RDBMS used by Odoo."
LangString DESC_FinishPage_Link ${LANG_ENGLISH} "Contact Odoo for Partnership and/or Support"
LangString DESC_AtLeastOneComponent ${LANG_ENGLISH} "You have to choose at least one component"
LangString DESC_CanNotInstallPostgreSQL ${LANG_ENGLISH} "You can not install the PostgreSQL database without the Odoo Server"
LangString WARNING_HostNameIsEmpty ${LANG_ENGLISH} "The hostname for the connection to the PostgreSQL Server is empty"
LangString WARNING_UserNameIsEmpty ${LANG_ENGLISH} "The username for the connection to the PostgreSQL Server is empty"
LangString WARNING_PasswordIsEmpty ${LANG_ENGLISH} "The password for the connection to the PostgreSQL Server is empty"
LangString WARNING_PortIsWrong ${LANG_ENGLISH} "The port for the connexion to the PostgreSQL Server is wrong (default: 5432)"
LangString DESC_PostgreSQLPage ${LANG_ENGLISH} "Configure the information for the PostgreSQL connection"
LangString DESC_PostgreSQL_Hostname ${LANG_ENGLISH} "Hostname"
LangString DESC_PostgreSQL_Port ${LANG_ENGLISH} "Port"
LangString DESC_PostgreSQL_Username ${LANG_ENGLISH} "Username"
LangString DESC_PostgreSQL_Password ${LANG_ENGLISH} "Password"
LangString Profile_AllInOne ${LANG_ENGLISH} "All In One"
LangString Profile_Server ${LANG_ENGLISH} "Server only"
LangString TITLE_OpenERP_Server ${LANG_ENGLISH} "Odoo Server"
LangString TITLE_PostgreSQL ${LANG_ENGLISH} "PostgreSQL Database"
LangString DESC_FinishPageText ${LANG_ENGLISH} "Start Odoo"

; French
LangString DESC_OpenERP_Server ${LANG_FRENCH} "Installation du Serveur Odoo avec tous les modules Odoo standards."
LangString DESC_PostgreSQL ${LANG_FRENCH} "Installation de la base de données PostgreSQL utilisée par Odoo."
LangString DESC_FinishPage_Link ${LANG_FRENCH} "Contactez Odoo pour un Partenariat et/ou du Support"
LangString DESC_AtLeastOneComponent ${LANG_FRENCH} "Vous devez choisir au moins un composant"
LangString DESC_CanNotInstallPostgreSQL ${LANG_FRENCH} "Vous ne pouvez pas installer la base de données PostgreSQL sans le serveur Odoo"
LangString WARNING_HostNameIsEmpty ${LANG_FRENCH} "L'adresse pour la connection au serveur PostgreSQL est vide"
LangString WARNING_UserNameIsEmpty ${LANG_FRENCH} "Le nom d'utilisateur pour la connection au serveur PostgreSQL est vide"
LangString WARNING_PasswordIsEmpty ${LANG_FRENCH} "Le mot de passe pour la connection au serveur PostgreSQL est vide"
LangString WARNING_PortIsWrong ${LANG_FRENCH} "Le port pour la connection au serveur PostgreSQL est erroné (défaut: 5432)"
LangString DESC_PostgreSQLPage ${LANG_FRENCH} "Configurez les informations de connection pour le serveur PostgreSQL"
LangString DESC_PostgreSQL_Hostname ${LANG_FRENCH} "Hôte"
LangString DESC_PostgreSQL_Port ${LANG_FRENCH} "Port"
LangString DESC_PostgreSQL_Username ${LANG_FRENCH} "Utilisateur"
LangString DESC_PostgreSQL_Password ${LANG_FRENCH} "Mot de passe"
LangString Profile_AllInOne ${LANG_FRENCH} "All In One"
LangString Profile_Server ${LANG_FRENCH} "Seulement le serveur"
LangString TITLE_OpenERP_Server ${LANG_FRENCH} "Serveur Odoo"
LangString TITLE_PostgreSQL ${LANG_FRENCH} "Installation du serveur de base de données PostgreSQL"
LangString DESC_FinishPageText ${LANG_FRENCH} "Démarrer Odoo"

InstType $(Profile_AllInOne)
InstType $(Profile_Server)

Section $(TITLE_OpenERP_Server) SectionOpenERP_Server
    SectionIn 1 2

    # TODO: install in a temp dir before
    
    # Installing winpython
    SetOutPath "$INSTDIR\python"
    File /r /x "__pycache__" "..\..\..\WinPython\python-3.6.2\*"

    SetOutPath "$INSTDIR\nssm"
    File /r /x "src" "..\..\..\nssm-2.24\*"

    SetOutPath "$INSTDIR\server"
    File /r /x "${POSTGRESQL_EXE_FILENAME}" /x "wkhtmltopdf" "..\..\*"

    SetOutPath "$INSTDIR\vcredist"
    File /r "..\..\..\vcredist\*.exe"
    
    # Install Visual C redistribuable files
    DetailPrint "Installing Visual C++ redistributable files"
    ${If} ${RunningX64}
        nsExec::Exec '"$INSTDIR\vcredist\vc_redist.x64.exe" /q'
    ${Else}
        nsExec::Exec '"$INSTDIR\vcredist\vc_redist.x86.exe" /q'
    ${EndIf}

    SetOutPath "$INSTDIR\thirdparty"
    File /r "${STATIC_PATH}\wkhtmltopdf\*"
    File /r "${STATIC_PATH}\less\*"

# If there is a previous install of the OpenERP Server, keep the login/password from the config file
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_host" $TextPostgreSQLHostname
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_user" $TextPostgreSQLUsername
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_password" $TextPostgreSQLPassword
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "db_port" $TextPostgreSQLPort
    # Fix the addons path
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "addons_path" "$INSTDIR\server\odoo\addons"
    WriteIniStr "$INSTDIR\server\odoo.conf" "options" "bin_path" "$INSTDIR\thirdparty"

    # if we're going to install postgresql force it's path,
    # otherwise we consider it's always done and/or correctly tune by users
    ${If} $HasPostgreSQL == 0
        WriteIniStr "$INSTDIR\server\odoo.conf" "options" "pg_path" "$INSTDIR\PostgreSQL\bin"
    ${EndIf}

    DetailPrint "Installing Windows service"
    nsExec::ExecTOLog '"$INSTDIR\python\python.exe" "$INSTDIR\server\odoo-bin" --stop-after-init --logfile "$INSTDIR\server\odoo.log" -s'
    ${If} ${RunningX64}
      nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" install ${SERVICENAME} "$INSTDIR\python\python.exe" "\"$INSTDIR\server\odoo-bin\""'
      nsExec::ExecToLog '"$INSTDIR\nssm\win64\nssm.exe" set ${SERVICENAME} AppDirectory "$\"$INSTDIR\server$\""'
    ${Else}
      nsExec::ExecToLog '"$INSTDIR\nssm\win32\nssm.exe" install ${SERVICENAME} "$INSTDIR\python\python.exe" "\"$INSTDIR\server\odoo-bin\""'
      nsExec::ExecToLog '"$INSTDIR\nssm\win32\nssm.exe" set ${SERVICENAME} AppDirectory "$\"$INSTDIR\server$\""'
    ${EndIf}
    
    nsExec::Exec "net stop ${SERVICENAME}"
    sleep 2

    nsExec::Exec "net start ${SERVICENAME}"
    sleep 2

SectionEnd
    
Section $(TITLE_PostgreSQL) SectionPostgreSQL
    SectionIn 1 2
    SetOutPath '$TEMP'
    nsExec::Exec 'net user openpgsvc /delete'

    File ${POSTGRESQL_EXE}

    ReadRegStr $0 HKLM "System\CurrentControlSet\Control\ComputerName\ActiveComputerName" "ComputerName"
    StrCmp $0 "" win9x
    Goto done
    win9x:
        ReadRegStr $0 HKLM "System\CurrentControlSet\Control\ComputerName\ComputerName" "ComputerName"
    done:
    Rmdir /r "$INSTDIR\PostgreSQL"
    ExecWait '"$TEMP\${POSTGRESQL_EXE_FILENAME}" \
        --mode unattended \
        --prefix "$INSTDIR\PostgreSQL" \
        --datadir "$INSTDIR\PostgreSQL\data" \
        --servicename "PostgreSQL_For_Odoo" \
        --serviceaccount "openpgsvc" --servicepassword "0p3npgsvcPWD" \
        --superaccount "$TextPostgreSQLUsername" --superpassword "$TextPostgreSQLPassword" \
        --serverport $TextPostgreSQLPort'
SectionEnd

Section -Post
    WriteRegExpandStr HKLM "${UNINSTALL_REGISTRY_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegExpandStr HKLM "${UNINSTALL_REGISTRY_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "DisplayName" "${DISPLAY_NAME}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "DisplayVersion" "${MAJOR_VERSION}.${MINOR_VERSION}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "Publisher" "${PUBLISHER}"
;    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "Version" "${VERSION}"
;    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "VersionMajor" "${MAJOR_VERSION}.${MINOR_VERSION}"
;    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "VersionMinor" "${REVISION_VERSION}"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "HelpLink" "support@odoo.com"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "HelpTelephone" "+32.81.81.37.00"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "URLInfoAbout" "https://www.odoo.com"
    WriteRegStr HKLM       "${UNINSTALL_REGISTRY_KEY}" "Contact" "sales@odoo.com"
    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "NoModify" "1"
    WriteRegDWORD HKLM     "${UNINSTALL_REGISTRY_KEY}" "NoRepair" "1"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SectionOpenERP_Server} $(DESC_OpenERP_Server)
    !insertmacro MUI_DESCRIPTION_TEXT ${SectionPostgreSQL} $(DESC_PostgreSQL)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
    # Check if the server is installed
    !insertmacro IfKeyExists "HKLM" "${UNINSTALL_REGISTRY_KEY_SERVER}" "UninstallString"
    Pop $R0
    ReadRegStr $0 HKLM "${UNINSTALL_REGISTRY_KEY_SERVER}" "UninstallString"
    ExecWait '"$0" /S'

    nsExec::Exec "net stop ${SERVICENAME}"
    nsExec::Exec "sc delete ${SERVICENAME}"
    sleep 2

    Rmdir /r "$INSTDIR\server"
    Rmdir /r "$INSTDIR\thirdparty"
    Rmdir /r "$INSTDIR\python"
    Rmdir /r "$INSTDIR\nssm"
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
    #SectionSetText ${SectionPostgreSQL} ""
    !insertmacro UnselectSection ${SectionPostgreSQL}
    SectionSetFlags ${SectionPostgreSQL} ${SF_RO}

    DoInstallPostgreSQL:
FunctionEnd

Function .onSelChange
    ${If} $HasPostgreSQL == 1
        !insertmacro UnselectSection ${SectionPostgreSQL}
    ${EndIf}
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

Function ComponentLeave
    SectionGetFlags ${SectionOpenERP_Server} $0
    IntOp $0 $0 & ${SF_SELECTED}
    IntCmp $0 ${SF_SELECTED} Done

    SectionGetFlags ${SectionPostgreSQL} $0
    IntOp $0 $0 & ${SF_SELECTED}
    IntCmp $0 ${SF_SELECTED} DontInstallPostgreSQL

    ChooseAtLeastOneComponent:
        MessageBox MB_ICONEXCLAMATION|MB_OK $(DESC_AtLeastOneComponent)
        Abort

    DontInstallPostgreSQL:
        MessageBox MB_ICONEXCLAMATION|MB_OK $(DESC_CanNotInstallPostgreSQL)
        Abort
    Done:
FunctionEnd

Function LaunchLink
    ExecShell "open" "http://localhost:8069/"
FunctionEnd
