; NSIS Modern User Interface
; Start Menu Folder Selection Example Script
; Written by Joost Verburg
; Modified By Stephane Wirtel - Tiny SPRL

;--------------------------------
;Include Modern UI

!include "MUI.nsh"

;--------------------------------
;General

;Name and file
Name "OpenERP Server"
OutFile "openerp-server-setup.exe"

;Default installation folder
InstallDir "$PROGRAMFILES\OpenERP Server"

;Get installation folder from registry if available
InstallDirRegKey HKCU "Software\OpenERP Server" ""

;Vista redirects $SMPROGRAMS to all users without this
RequestExecutionLevel admin

;--------------------------------
;Variables

Var MUI_TEMP
Var STARTMENU_FOLDER

;--------------------------------
;Interface Settings

!define MUI_ABORTWARNING

;--------------------------------
;Pages

!define MUI_ICON ".\pixmaps\openerp.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP ".\pixmaps\openerp-intro.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP ".\pixmaps\openerp-intro.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP_NOSTRETCH
!define MUI_HEADER_TRANSPARENT_TEXT ""
!define MUI_HEADERIMAGE_BITMAP ".\pixmaps\openerp-slogan.bmp"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "doc\\License.rtf"
# !insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY

;Start Menu Folder Page Configuration
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU" 
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\OpenERP Server"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "OpenERP Server"

!insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER

!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_NOAUTOCLOSE
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_CHECKED
!define MUI_FINISHPAGE_RUN_TEXT "Start OpenERP Server"
!define MUI_FINISHPAGE_RUN_FUNCTION "LaunchLink"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!define MUI_FINISHPAGE_SHOWREADME $INSTDIR\README.txt
!insertmacro MUI_PAGE_FINISH


!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
;Languages

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "OpenERP Server" SecOpenERPServer

    nsExec::Exec "net stop openerp-service"
    sleep 2

    SetOutPath "$INSTDIR"

    ;ADD YOUR OWN FILES HERE...
    File /r "dist\\*"

    SetOutPath "$INSTDIR\service"
    File /r "win32\\dist\\*"
    File "win32\\start.bat"
    File "win32\\stop.bat"

    ;Store installation folder
    WriteRegStr HKCU "Software\OpenERP Server" "" $INSTDIR

    ;Create uninstaller
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenERP Server" "DisplayName" "OpenERP Server 5.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenERP Server" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
        ;Create shortcuts
        CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\OpenERP Server.lnk" "$INSTDIR\openerp-server.exe"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Start service.lnk" "$INSTDIR\service\start.bat"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Stop service.lnk" "$INSTDIR\service\stop.bat"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Edit config.lnk" "notepad.exe" "$INSTDIR\openerp-server.conf"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\View log.lnk" "notepad.exe" "$INSTDIR\openerp-server.log"
        CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    !insertmacro MUI_STARTMENU_WRITE_END

    nsExec::Exec '"$INSTDIR\\openerp-server.exe" --stop-after-init --logfile "$INSTDIR\\openerp-server.log" -s'
    nsExec::Exec '"$INSTDIR\\service\\OpenERPServerService.exe" -auto -install'

SectionEnd

;Descriptions

;Language strings
LangString DESC_SecOpenERPServer ${LANG_ENGLISH} "OpenERP Server."

;Assign language strings to sections
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecOpenERPServer} $(DESC_SecOpenERPServer)
!insertmacro MUI_FUNCTION_DESCRIPTION_END
 
;--------------------------------
;Uninstaller Section

Section "Uninstall"

    nsExec::Exec "net stop openerp-service"
    sleep 2
    nsExec::Exec '"$INSTDIR\\service\\OpenERPServerService.exe" -remove'
    sleep 2

    RMDIR /r "$INSTDIR" 
    !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP

    Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\OpenERP Server.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Start service.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Stop service.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\Edit config.lnk"
    Delete "$SMPROGRAMS\$MUI_TEMP\View log.lnk"

    ;Delete empty start menu parent diretories
    StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"
 
    startMenuDeleteLoop:
        ClearErrors
        RMDir $MUI_TEMP
        GetFullPathName $MUI_TEMP "$MUI_TEMP\.."

        IfErrors startMenuDeleteLoopDone

        StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop

    startMenuDeleteLoopDone:

        DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\OpenERP Server"
        DeleteRegKey /ifempty HKCU "Software\OpenERP Server"

SectionEnd

Function LaunchLink
    nsExec::Exec "net start openerp-service"
FunctionEnd

