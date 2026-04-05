/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {
    Accordion,
    AccordionContent,
    AccordionHeader,
    AccordionItem,
    AccordionTrigger,
} from "@odx_owl/components/accordion/accordion";
import { Alert, AlertDescription, AlertTitle } from "@odx_owl/components/alert/alert";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogOverlay,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@odx_owl/components/alert_dialog/alert_dialog";
import { AspectRatio } from "@odx_owl/components/aspect_ratio/aspect_ratio";
import { Avatar, AvatarFallback, AvatarImage } from "@odx_owl/components/avatar/avatar";
import { Badge } from "@odx_owl/components/badge/badge";
import { ButtonGroup, ButtonGroupSeparator, ButtonGroupText } from "@odx_owl/components/button_group/button_group";
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    BreadcrumbList,
    BreadcrumbPage,
    BreadcrumbSeparator,
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from "@odx_owl/components/breadcrumb/breadcrumb";
import { Button } from "@odx_owl/components/button/button";
import {
    Carousel,
    CarouselContent,
    CarouselItem,
    CarouselNext,
    CarouselPrevious,
} from "@odx_owl/components/carousel/carousel";
import {
    BarChart,
    ChartContainer,
    ChartLegend,
    ChartLegendContent,
    ChartTooltip,
    ChartTooltipContent,
    DonutChart,
    LineChart,
} from "@odx_owl/components/chart/chart";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@odx_owl/components/card/card";
import { Calendar } from "@odx_owl/components/calendar/calendar";
import { Checkbox } from "@odx_owl/components/checkbox/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@odx_owl/components/collapsible/collapsible";
import {
    Combobox,
    ComboboxContent,
    ComboboxIcon,
    ComboboxTrigger,
    ComboboxValue,
} from "@odx_owl/components/combobox/combobox";
import {
    Command,
    CommandDialog,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandItemDescription,
    CommandItemText,
    CommandList,
    CommandLoading,
    CommandSeparator,
    CommandShortcut,
} from "@odx_owl/components/command/command";
import {
    ContextMenu,
    ContextMenuCheckboxItem,
    ContextMenuContent,
    ContextMenuGroup,
    ContextMenuItem,
    ContextMenuLabel,
    ContextMenuRadioGroup,
    ContextMenuRadioItem,
    ContextMenuSeparator,
    ContextMenuShortcut,
    ContextMenuSub,
    ContextMenuSubContent,
    ContextMenuSubTrigger,
    ContextMenuTrigger,
} from "@odx_owl/components/context_menu/context_menu";
import { DataTable } from "@odx_owl/components/data_table/data_table";
import { DatePicker } from "@odx_owl/components/date_picker/date_picker";
import { DateRangePicker } from "@odx_owl/components/date_range_picker/date_range_picker";
import {
    Dialog,
    DialogDescription,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogOverlay,
    DialogTitle,
    DialogTrigger,
    DialogClose,
} from "@odx_owl/components/dialog/dialog";
import {
    Drawer,
    DrawerClose,
    DrawerContent,
    DrawerDescription,
    DrawerFooter,
    DrawerHeader,
    DrawerOverlay,
    DrawerTitle,
    DrawerTrigger,
} from "@odx_owl/components/drawer/drawer";
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuRadioGroup,
    DropdownMenuRadioItem,
    DropdownMenuSeparator,
    DropdownMenuSub,
    DropdownMenuSubContent,
    DropdownMenuSubTrigger,
    DropdownMenuShortcut,
    DropdownMenuTrigger,
} from "@odx_owl/components/dropdown_menu/dropdown_menu";
import {
    Empty,
    EmptyContent,
    EmptyDescription,
    EmptyHeader,
    EmptyMedia,
    EmptyTitle,
} from "@odx_owl/components/empty/empty";
import {
    Field,
    FieldContent,
    FieldDescription,
    FieldError,
    FieldGroup,
    FieldLabel,
    FieldLegend,
    FieldSeparator,
    FieldSet,
    FieldTitle,
} from "@odx_owl/components/field/field";
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@odx_owl/components/form/form";
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from "@odx_owl/components/hover_card/hover_card";
import { Input } from "@odx_owl/components/input/input";
import {
    InputGroup,
    InputGroupAddon,
    InputGroupButton,
    InputGroupInput,
    InputGroupText,
    InputGroupTextarea,
} from "@odx_owl/components/input_group/input_group";
import { InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot } from "@odx_owl/components/input_otp/input_otp";
import {
    Item,
    ItemActions,
    ItemContent,
    ItemDescription,
    ItemFooter,
    ItemGroup,
    ItemHeader,
    ItemMedia,
    ItemSeparator,
    ItemTitle,
} from "@odx_owl/components/item/item";
import { Kbd, KbdGroup } from "@odx_owl/components/kbd/kbd";
import { Label } from "@odx_owl/components/label/label";
import {
    Menubar,
    MenubarCheckboxItem,
    MenubarContent,
    MenubarGroup,
    MenubarItem,
    MenubarLabel,
    MenubarMenu,
    MenubarRadioGroup,
    MenubarRadioItem,
    MenubarSeparator,
    MenubarShortcut,
    MenubarSub,
    MenubarSubContent,
    MenubarSubTrigger,
    MenubarTrigger,
} from "@odx_owl/components/menubar/menubar";
import {
    NavigationMenu,
    NavigationMenuContent,
    NavigationMenuIndicator,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    NavigationMenuTrigger,
    NavigationMenuViewport,
} from "@odx_owl/components/navigation_menu/navigation_menu";
import { NativeSelect } from "@odx_owl/components/native_select/native_select";
import {
    Popover,
    PopoverAnchor,
    PopoverClose,
    PopoverContent,
    PopoverTrigger,
} from "@odx_owl/components/popover/popover";
import { Progress } from "@odx_owl/components/progress/progress";
import { RadioGroup, RadioGroupItem } from "@odx_owl/components/radio_group/radio_group";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@odx_owl/components/resizable/resizable";
import { ScrollArea } from "@odx_owl/components/scroll_area/scroll_area";
import { Separator } from "@odx_owl/components/separator/separator";
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectIcon,
    SelectItem,
    SelectItemDescription,
    SelectItemIndicator,
    SelectItemText,
    SelectLabel,
    SelectScrollDownButton,
    SelectScrollUpButton,
    SelectSeparator,
    SelectTrigger,
    SelectValue,
    SelectViewport,
} from "@odx_owl/components/select/select";
import {
    Sheet,
    SheetClose,
    SheetContent,
    SheetDescription,
    SheetFooter,
    SheetHeader,
    SheetOverlay,
    SheetTitle,
    SheetTrigger,
} from "@odx_owl/components/sheet/sheet";
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupAction,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarInput,
    SidebarInset,
    SidebarMenu,
    SidebarMenuAction,
    SidebarMenuBadge,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuSub,
    SidebarMenuSubButton,
    SidebarMenuSubItem,
    SidebarProvider,
    SidebarRail,
    SidebarSeparator,
    SidebarTrigger,
} from "@odx_owl/components/sidebar/sidebar";
import { Skeleton } from "@odx_owl/components/skeleton/skeleton";
import { Slider } from "@odx_owl/components/slider/slider";
import { Spinner } from "@odx_owl/components/spinner/spinner";
import { Switch } from "@odx_owl/components/switch/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@odx_owl/components/tabs/tabs";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@odx_owl/components/table/table";
import { Textarea } from "@odx_owl/components/textarea/textarea";
import { Toggle } from "@odx_owl/components/toggle/toggle";
import { ToggleGroup, ToggleGroupItem } from "@odx_owl/components/toggle_group/toggle_group";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@odx_owl/components/tooltip/tooltip";
import { formatDateRangeValue, formatDateValue } from "@odx_owl/core/utils/dates";

export class OdxOwlDocsApp extends Component {
    static template = "odx_owl.DocsApp";
    static components = {
        Accordion,
        AccordionContent,
        AccordionHeader,
        AccordionItem,
        AccordionTrigger,
        Alert,
        AlertDescription,
        AlertDialog,
        AlertDialogAction,
        AlertDialogCancel,
        AlertDialogContent,
        AlertDialogDescription,
        AlertDialogFooter,
        AlertDialogHeader,
        AlertDialogOverlay,
        AlertDialogTitle,
        AlertDialogTrigger,
        AlertTitle,
        AspectRatio,
        Avatar,
        AvatarFallback,
        AvatarImage,
        Badge,
        ButtonGroup,
        ButtonGroupSeparator,
        ButtonGroupText,
        Breadcrumb,
        BreadcrumbItem,
        BreadcrumbLink,
        BreadcrumbList,
        BreadcrumbPage,
        BreadcrumbSeparator,
        Button,
        BarChart,
        Calendar,
        Carousel,
        CarouselContent,
        CarouselItem,
        CarouselNext,
        CarouselPrevious,
        ChartContainer,
        ChartLegend,
        ChartLegendContent,
        ChartTooltip,
        ChartTooltipContent,
        Card,
        CardContent,
        CardDescription,
        CardFooter,
        CardHeader,
        CardTitle,
        Checkbox,
        Collapsible,
        CollapsibleContent,
        CollapsibleTrigger,
        Combobox,
        ComboboxContent,
        ComboboxIcon,
        ComboboxTrigger,
        ComboboxValue,
        Command,
        CommandDialog,
        CommandEmpty,
        CommandGroup,
        CommandInput,
        CommandItem,
        CommandItemDescription,
        CommandItemText,
        CommandList,
        CommandLoading,
        CommandSeparator,
        CommandShortcut,
        ContextMenu,
        ContextMenuCheckboxItem,
        ContextMenuContent,
        ContextMenuGroup,
        ContextMenuItem,
        ContextMenuLabel,
        ContextMenuRadioGroup,
        ContextMenuRadioItem,
        ContextMenuSeparator,
        ContextMenuShortcut,
        ContextMenuSub,
        ContextMenuSubContent,
        ContextMenuSubTrigger,
        ContextMenuTrigger,
        DataTable,
        DatePicker,
        DateRangePicker,
        Dialog,
        DialogClose,
        DialogContent,
        DialogDescription,
        DialogFooter,
        DialogHeader,
        DialogOverlay,
        DialogTitle,
        DialogTrigger,
        Drawer,
        DrawerClose,
        DrawerContent,
        DrawerDescription,
        DrawerFooter,
        DrawerHeader,
        DrawerOverlay,
        DrawerTitle,
        DrawerTrigger,
        DropdownMenu,
        DropdownMenuCheckboxItem,
        DropdownMenuContent,
        DropdownMenuGroup,
        DropdownMenuItem,
        DropdownMenuLabel,
        DropdownMenuRadioGroup,
        DropdownMenuRadioItem,
        DropdownMenuSeparator,
        DropdownMenuSub,
        DropdownMenuSubContent,
        DropdownMenuSubTrigger,
        DropdownMenuShortcut,
        DropdownMenuTrigger,
        DonutChart,
        Empty,
        EmptyContent,
        EmptyDescription,
        EmptyHeader,
        EmptyMedia,
        EmptyTitle,
        Field,
        FieldContent,
        FieldDescription,
        FieldError,
        FieldGroup,
        FieldLabel,
        FieldLegend,
        FieldSeparator,
        FieldSet,
        FieldTitle,
        Form,
        FormControl,
        FormDescription,
        FormField,
        FormItem,
        FormLabel,
        FormMessage,
        HoverCard,
        HoverCardContent,
        HoverCardTrigger,
        Input,
        InputGroup,
        InputGroupAddon,
        InputGroupButton,
        InputGroupInput,
        InputGroupText,
        InputGroupTextarea,
        InputOTP,
        InputOTPGroup,
        InputOTPSeparator,
        InputOTPSlot,
        Item,
        ItemActions,
        ItemContent,
        ItemDescription,
        ItemFooter,
        ItemGroup,
        ItemHeader,
        ItemMedia,
        ItemSeparator,
        ItemTitle,
        Kbd,
        KbdGroup,
        Label,
        LineChart,
        Menubar,
        MenubarCheckboxItem,
        MenubarContent,
        MenubarGroup,
        MenubarItem,
        MenubarLabel,
        MenubarMenu,
        MenubarRadioGroup,
        MenubarRadioItem,
        MenubarSeparator,
        MenubarShortcut,
        MenubarSub,
        MenubarSubContent,
        MenubarSubTrigger,
        MenubarTrigger,
        NavigationMenu,
        NavigationMenuContent,
        NavigationMenuIndicator,
        NavigationMenuItem,
        NavigationMenuLink,
        NavigationMenuList,
        NavigationMenuTrigger,
        NavigationMenuViewport,
        NativeSelect,
        Pagination,
        PaginationContent,
        PaginationEllipsis,
        PaginationItem,
        PaginationLink,
        PaginationNext,
        PaginationPrevious,
        Popover,
        PopoverAnchor,
        PopoverClose,
        PopoverContent,
        PopoverTrigger,
        Progress,
        RadioGroup,
        RadioGroupItem,
        ResizableHandle,
        ResizablePanel,
        ResizablePanelGroup,
        ScrollArea,
        Separator,
        Select,
        SelectContent,
        SelectGroup,
        SelectIcon,
        SelectItem,
        SelectItemDescription,
        SelectItemIndicator,
        SelectItemText,
        SelectLabel,
        SelectScrollDownButton,
        SelectScrollUpButton,
        SelectSeparator,
        SelectTrigger,
        SelectValue,
        SelectViewport,
        Sheet,
        SheetClose,
        SheetContent,
        SheetDescription,
        SheetFooter,
        SheetHeader,
        SheetOverlay,
        SheetTitle,
        SheetTrigger,
        Sidebar,
        SidebarContent,
        SidebarFooter,
        SidebarGroup,
        SidebarGroupAction,
        SidebarGroupContent,
        SidebarGroupLabel,
        SidebarHeader,
        SidebarInput,
        SidebarInset,
        SidebarMenu,
        SidebarMenuAction,
        SidebarMenuBadge,
        SidebarMenuButton,
        SidebarMenuItem,
        SidebarMenuSub,
        SidebarMenuSubButton,
        SidebarMenuSubItem,
        SidebarProvider,
        SidebarRail,
        SidebarSeparator,
        SidebarTrigger,
        Skeleton,
        Slider,
        Spinner,
        Switch,
        Tabs,
        TabsContent,
        TabsList,
        TabsTrigger,
        Table,
        TableBody,
        TableCell,
        TableHead,
        TableHeader,
        TableRow,
        Textarea,
        Toggle,
        ToggleGroup,
        ToggleGroupItem,
        Tooltip,
        TooltipContent,
        TooltipProvider,
        TooltipTrigger,
    };
    static props = {
        action: { optional: true },
        actionId: { optional: true },
        updateActionState: { optional: true },
        className: { type: String, optional: true },
        mode: { type: String, optional: true },
    };
    static defaultProps = {
        mode: "backend",
    };

    setup() {
        this.theme = useService("odx_theme");
        this.toast = useService("odx_toast");
        this.form = useState({
            email: "design@preview.odx",
            name: "Ada Lovelace",
            note: "The component tokens stay aligned across backend actions, portal pages, and nested module usage.",
            inviteCode: "482901",
            workspaceSlug: "registry/odx-owl",
            compact: true,
            releaseAlerts: true,
            betaAccess: "indeterminate",
            automaticDeploys: true,
            reviewPolicy: "manual",
            releaseDate: new Date(2026, 2, 24),
            releaseWindow: {
                from: new Date(2026, 2, 24),
                to: new Date(2026, 2, 30),
            },
            syncProgress: 72,
            stack: "owl",
            surface: "portal",
            compactToolbar: true,
            formatting: ["bold", "italic"],
            releaseGuardrail: [35, 80],
            zoom: 56,
        });
    }

    get stackItems() {
        return [
            {
                value: "owl",
                label: "OWL",
                description: "Odoo-native interactive views",
                group: "Core",
                keywords: "odoo web client component",
            },
            {
                value: "portal",
                label: "Portal",
                description: "Shared experience for authenticated website users",
                group: "Core",
                keywords: "website frontend portal",
            },
            {
                value: "builder",
                label: "Builder",
                description: "Composable UI for editors and page authors",
                group: "Extension",
                keywords: "visual editor low code",
            },
            {
                value: "spreadsheet",
                label: "Spreadsheet",
                description: "Data-heavy productivity surfaces",
                group: "Extension",
                keywords: "analytics sheet grid",
            },
        ];
    }

    get chartConfig() {
        return {
            visitors: {
                label: "Visitors",
                color: "hsl(var(--odx-chart-1))",
            },
            signups: {
                label: "Signups",
                color: "hsl(var(--odx-chart-2))",
            },
            portal: {
                label: "Portal",
                color: "hsl(var(--odx-chart-1))",
            },
            builder: {
                label: "Builder",
                color: "hsl(var(--odx-chart-3))",
            },
            backend: {
                label: "Backend",
                color: "hsl(var(--odx-chart-5))",
            },
        };
    }

    get trafficChartData() {
        return [
            { period: "Mon", visitors: 148, signups: 32 },
            { period: "Tue", visitors: 172, signups: 41 },
            { period: "Wed", visitors: 196, signups: 52 },
            { period: "Thu", visitors: 184, signups: 47 },
            { period: "Fri", visitors: 231, signups: 61 },
            { period: "Sat", visitors: 208, signups: 58 },
        ];
    }

    get releaseChartData() {
        return [
            { sprint: "S1", portal: 12, builder: 8, backend: 10 },
            { sprint: "S2", portal: 16, builder: 11, backend: 13 },
            { sprint: "S3", portal: 18, builder: 15, backend: 14 },
            { sprint: "S4", portal: 22, builder: 18, backend: 17 },
        ];
    }

    get surfaceShareData() {
        return [
            { name: "portal", value: 42 },
            { name: "builder", value: 33 },
            { name: "backend", value: 25 },
        ];
    }

    get carouselSlides() {
        return [
            {
                badge: "Portal",
                title: "Account review flow",
                description: "Reusable drawers, forms, and badges shape a customer-facing approval flow without introducing a second design language.",
            },
            {
                badge: "Builder",
                title: "Visual editor shell",
                description: "Inset sidebars, tabs, and resizable panels create a composable workspace for content tooling and low-code surfaces.",
            },
            {
                badge: "Backend",
                title: "Admin quality board",
                description: "Dense navigation, menus, tables, and toasts keep operational tooling aligned with the same token system.",
            },
        ];
    }

    get releaseBoardColumns() {
        return [
            {
                key: "surface",
                label: "Surface",
                sortable: true,
                descriptionKey: "track",
            },
            {
                key: "status",
                label: "Status",
                sortable: true,
                type: "badge",
                variantMap: {
                    Stable: "secondary",
                    Review: "outline",
                    Draft: "default",
                },
            },
            {
                key: "owner",
                label: "Owner",
                sortable: true,
                descriptionKey: "team",
            },
            {
                key: "updatedLabel",
                label: "Updated",
                align: "end",
                sortable: true,
                formatter: (value) => value,
                sortAccessor: (row) => row.updatedMinutes,
            },
        ];
    }

    get releaseBoardRows() {
        return [
            {
                id: "backend",
                owner: "Ada Lovelace",
                status: "Stable",
                surface: "Backend web client",
                team: "Core registry",
                track: "Shell and action registry",
                updatedLabel: "2 min ago",
                updatedMinutes: 2,
            },
            {
                id: "portal",
                owner: "Grace Hopper",
                status: "Review",
                surface: "Portal preview",
                team: "Experience systems",
                track: "Customer account flows",
                updatedLabel: "12 min ago",
                updatedMinutes: 12,
            },
            {
                id: "builder",
                owner: "Alan Kay",
                status: "Draft",
                surface: "Builder palette",
                team: "Content tooling",
                track: "Low-code editing canvas",
                updatedLabel: "38 min ago",
                updatedMinutes: 38,
            },
            {
                id: "analytics",
                owner: "Margaret Hamilton",
                status: "Stable",
                surface: "Analytics cockpit",
                team: "Operations",
                track: "Chart and reporting surfaces",
                updatedLabel: "51 min ago",
                updatedMinutes: 51,
            },
            {
                id: "support",
                owner: "Katherine Johnson",
                status: "Review",
                surface: "Support portal",
                team: "Service desk",
                track: "Helpdesk and ticket routing",
                updatedLabel: "1 hr ago",
                updatedMinutes: 64,
            },
            {
                id: "studio",
                owner: "Radia Perlman",
                status: "Draft",
                surface: "Studio integrations",
                team: "Platform",
                track: "Extension and embedding points",
                updatedLabel: "2 hr ago",
                updatedMinutes: 132,
            },
        ];
    }

    get releaseBoardDefaultSort() {
        return {
            key: "updatedLabel",
            direction: "asc",
        };
    }

    get surfaceItems() {
        return [
            {
                value: "backend",
                label: "Web client",
                description: "Admin-facing workflows and client actions",
                group: "Distribution",
            },
            {
                value: "portal",
                label: "Portal",
                description: "Customer-facing authenticated pages",
                group: "Distribution",
            },
            {
                value: "public",
                label: "Public website",
                description: "Anonymous marketing or documentation pages",
                group: "Distribution",
            },
        ];
    }

    get commandItems() {
        return [
            {
                value: "open-theme",
                label: "Toggle theme",
                description: "Switch between the current light and dark palettes.",
                group: "Actions",
                shortcut: "Shift T",
            },
            {
                value: "toast-success",
                label: "Show success toast",
                description: "Dispatch a shared toast event from the active service.",
                group: "Actions",
                shortcut: "Enter",
            },
            {
                value: "toast-danger",
                label: "Show destructive toast",
                description: "Preview the destructive visual treatment and messaging.",
                group: "Actions",
                shortcut: "Del",
            },
            {
                value: "open-preview",
                label: "Open portal preview",
                description: "Jump to the public preview route for the same asset bundle.",
                group: "Navigation",
                shortcut: "/",
            },
        ];
    }

    get docsMenuItems() {
        return [
            { type: "label", label: "Library actions" },
            {
                label: "Show success toast",
                onSelected: () => this.showToast(),
                shortcut: "Shift+T",
            },
            {
                label: this.form.compact ? "Disable compact density" : "Enable compact density",
                type: "checkbox",
                checked: this.form.compact,
                onSelected: () => {
                    this.form.compact = !this.form.compact;
                },
            },
            { type: "separator" },
            {
                label: "Show destructive toast",
                destructive: true,
                onSelected: () => this.showDestructiveToast(),
                shortcut: "Del",
            },
            {
                type: "submenu",
                label: "Jump to surface",
                items: [
                    {
                        label: "Portal preview",
                        shortcut: "P",
                        onSelected: () => this.announcePreviewRoute(),
                    },
                    {
                        label: "Release workspace",
                        shortcut: "R",
                        onSelected: () => this.showToast(),
                    },
                ],
            },
        ];
    }

    get menubarMenus() {
        return [
            {
                label: "File",
                items: [
                    {
                        label: "Save workspace",
                        shortcut: "Cmd+S",
                        onSelected: () => this.saveDemoRecord(),
                    },
                    {
                        label: "Open preview route",
                        shortcut: "Shift+P",
                        onSelected: () => this.announcePreviewRoute(),
                    },
                    { type: "separator" },
                    {
                        label: "Export",
                        type: "submenu",
                        items: [
                            {
                                label: "Portal snapshot",
                                shortcut: "P",
                                onSelected: () => this.showToast(),
                            },
                            {
                                label: "Release summary",
                                shortcut: "R",
                                onSelected: () => this.showToast(),
                            },
                        ],
                    },
                ],
            },
            {
                label: "View",
                items: [
                    {
                        label: this.theme.resolvedTheme === "dark" ? "Switch to light mode" : "Switch to dark mode",
                        shortcut: "Shift+T",
                        onSelected: () => this.theme.toggleTheme(),
                    },
                    {
                        label: "Compact density",
                        type: "checkbox",
                        checked: this.form.compact,
                        onSelected: () => {
                            this.form.compact = !this.form.compact;
                        },
                    },
                    {
                        label: "Compact toolbar",
                        type: "checkbox",
                        checked: this.form.compactToolbar,
                        onSelected: () => {
                            this.form.compactToolbar = !this.form.compactToolbar;
                        },
                    },
                ],
            },
            {
                label: "Help",
                items: [
                    {
                        label: "Show success toast",
                        onSelected: () => this.showToast(),
                    },
                    {
                        label: "Show destructive toast",
                        destructive: true,
                        onSelected: () => this.showDestructiveToast(),
                    },
                ],
            },
        ];
    }

    get contextMenuItems() {
        return [
            { type: "label", label: "Canvas actions" },
            {
                label: "Open command palette",
                shortcut: "Cmd+K",
                onSelected: () => this.showToast(),
            },
            {
                label: "Automatic deploys",
                type: "checkbox",
                checked: this.form.automaticDeploys,
                onSelected: () => {
                    this.form.automaticDeploys = !this.form.automaticDeploys;
                },
            },
            { type: "separator" },
            {
                label: "Archive workspace",
                destructive: true,
                shortcut: "Del",
                onSelected: () => this.archiveWorkspace(),
            },
            {
                type: "submenu",
                label: "Jump to",
                items: [
                    {
                        label: "Portal preview",
                        shortcut: "P",
                        onSelected: () => this.announcePreviewRoute(),
                    },
                    {
                        label: "Success toast",
                        shortcut: "T",
                        onSelected: () => this.showToast(),
                    },
                ],
            },
        ];
    }

    get navigationMenuItems() {
        return [
            {
                label: "Overview",
                value: "overview",
                columns: 2,
                featured: {
                    eyebrow: "Foundation",
                    title: "ODX OWL for Odoo 19",
                    description: "Shared components, tokens, and services for backend client actions, portal pages, and builders.",
                    href: "#",
                },
                items: [
                    {
                        title: "Installation",
                        description: "Mount the bundle once and reuse the same primitives across addons.",
                        href: "#",
                    },
                    {
                        title: "Theme tokens",
                        description: "Light, dark, and semantic variables aligned across backend and portal surfaces.",
                        href: "#",
                    },
                    {
                        title: "Accessibility",
                        description: "Keyboard handling, ARIA state, overlays, and visible focus rings built in.",
                        href: "#",
                    },
                ],
            },
            {
                label: "Components",
                value: "components",
                columns: 3,
                items: [
                    {
                        title: "Overlays",
                        description: "Dialog, sheet, popover, hover card, and alert dialog.",
                        href: "#",
                    },
                    {
                        title: "Selection",
                        description: "Select, combobox, radio group, checkbox, switch, and slider.",
                        href: "#",
                    },
                    {
                        title: "Navigation",
                        description: "Breadcrumb, pagination, menubar, context menu, and navigation menu.",
                        href: "#",
                    },
                    {
                        title: "Data display",
                        description: "Card, table, badge, alert, progress, and skeleton.",
                        href: "#",
                    },
                    {
                        title: "Layout",
                        description: "Tabs, accordion, aspect ratio, scroll area, and separator.",
                        href: "#",
                    },
                    {
                        title: "Feedback",
                        description: "Toasts, destructive states, and command-driven quick actions.",
                        href: "#",
                    },
                ],
            },
            {
                label: "Portal",
                href: "#",
                onSelected: () => this.announcePreviewRoute(),
            },
            {
                label: "Patterns",
                value: "patterns",
                columns: 2,
                items: [
                    {
                        title: "Builder shell",
                        description: "Toolbar, inspector, and layered content editing workflows.",
                        href: "#",
                    },
                    {
                        title: "Admin console",
                        description: "Dense data-entry and navigation-heavy internal tooling.",
                        href: "#",
                    },
                    {
                        title: "Portal workspace",
                        description: "Reusable account, helpdesk, and customer portal surfaces.",
                        href: "#",
                    },
                    {
                        title: "Embedded widgets",
                        description: "Small module-level surfaces that inherit the same tokens and a11y primitives.",
                        href: "#",
                    },
                ],
            },
        ];
    }

    get isFrontend() {
        return this.props.mode === "frontend";
    }

    get demoFormDescriptions() {
        return {
            email: "Use the same field wrappers in backend client actions, portal forms, and embedded builders.",
            name: "This value is reused in overlays, avatars, and quick settings throughout the gallery.",
            note: "Descriptions and messages wire themselves to the control through shared form context.",
        };
    }

    get demoFormErrors() {
        const errors = {};
        if (this.form.name.trim().length < 3) {
            errors.name = "Name must contain at least 3 characters.";
        }
        if (!/@odx\.local$/i.test(this.form.email.trim())) {
            errors.email = "Use an internal @odx.local address for this preview.";
        }
        if (this.form.note.trim().length < 32) {
            errors.note = "Add a little more context so helper text and validation states both render clearly.";
        }
        return errors;
    }

    get demoFormErrorItems() {
        return Object.values(this.demoFormErrors)
            .filter(Boolean)
            .map((message) => ({ message }));
    }

    get hasDemoFormErrors() {
        return Object.values(this.demoFormErrors).some(Boolean);
    }

    get otpValueLabel() {
        return this.form.inviteCode || "Pending";
    }

    get workspaceItems() {
        return [
            {
                title: "Registry review",
                description: "Audit new primitives for portal and web client parity before the next release cut.",
                meta: "Design Systems",
                status: "In review",
            },
            {
                title: "Portal builder",
                description: "Ship grouped field layouts, empty states, and input scaffolding to downstream addons.",
                meta: "Shared UI",
                status: "Ready",
            },
            {
                title: "Accessibility sweep",
                description: "Verify disclosure, focus movement, and field messaging across composite patterns.",
                meta: "Quality",
                status: "Queued",
            },
        ];
    }

    get releaseDateDisabledMatcher() {
        return (date) => [0, 6].includes(date.getDay());
    }

    get releaseDateLabel() {
        return formatDateValue(this.form.releaseDate, { dateStyle: "full" }) || "Not scheduled";
    }

    get releaseWindowLabel() {
        return (
            formatDateRangeValue(this.form.releaseWindow, {
                month: "short",
                day: "2-digit",
                year: "numeric",
            }) || "No release window"
        );
    }

    get releaseWindowEnd() {
        return new Date(2026, 3, 18);
    }

    get releaseWindowStart() {
        return new Date(2026, 2, 18);
    }

    get rootClasses() {
        return this.isFrontend ? "odx-docs odx-docs--frontend" : "odx-docs odx-docs--backend";
    }

    get profileInitials() {
        const initials = this.form.name
            .split(/\s+/)
            .filter(Boolean)
            .map((part) => part[0])
            .slice(0, 2)
            .join("")
            .toUpperCase();
        return initials || "OD";
    }

    get profileAvatarSrc() {
        const svg = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96">
                <defs>
                    <linearGradient id="odx-avatar-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stop-color="#111827"/>
                        <stop offset="100%" stop-color="#475569"/>
                    </linearGradient>
                </defs>
                <rect width="96" height="96" rx="48" fill="url(#odx-avatar-gradient)"/>
                <text
                    x="48"
                    y="56"
                    fill="#f8fafc"
                    font-family="IBM Plex Sans, Segoe UI, sans-serif"
                    font-size="28"
                    font-weight="600"
                    text-anchor="middle"
                >${this.profileInitials}</text>
            </svg>
        `.trim();
        return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
    }

    showToast() {
        this.toast.add({
            title: "Component event dispatched",
            description: "The odx_owl toast service is available from any OWL component through useService('odx_toast').",
            actionLabel: "Undo",
            action: () => {
                this.toast.add({
                    title: "Undo ready",
                    description: "Actions can cascade into follow-up notifications.",
                });
            },
        });
    }

    showDestructiveToast() {
        this.toast.add({
            variant: "destructive",
            title: "Destructive variant",
            description: "Shared variants map to the same tokens in backend and portal contexts.",
        });
    }

    updateField(field, value) {
        this.form[field] = value;
    }

    saveDemoRecord() {
        this.toast.add({
            title: "Demo payload saved",
            description: `${this.form.name} <${this.form.email}>`,
        });
    }

    previewTableRow(row) {
        this.toast.add({
            title: row.surface,
            description: `${row.status} surface owned by ${row.owner}.`,
        });
    }

    inspectTableRow(row) {
        this.toast.add({
            title: "Inspect row",
            description: `${row.track} for ${row.team}.`,
        });
    }

    completeInviteCode(value) {
        this.toast.add({
            title: "OTP complete",
            description: `Captured code ${value}.`,
        });
    }

    submitDemoForm() {
        if (this.hasDemoFormErrors) {
            this.toast.add({
                variant: "destructive",
                title: "Resolve validation errors",
                description: Object.values(this.demoFormErrors).find(Boolean),
            });
            return;
        }
        this.saveDemoRecord();
    }

    archiveWorkspace() {
        this.toast.add({
            variant: "destructive",
            title: "Workspace archived",
            description: "The alert dialog confirm action reused the same shared button and dialog tokens.",
        });
    }

    announcePreviewRoute() {
        this.toast.add({
            title: "Preview route",
            description: "Open /odx_owl/preview in the current Odoo instance to validate the portal bundle.",
        });
    }

    runCommand(value) {
        if (value === "open-theme") {
            this.theme.toggleTheme();
            this.toast.add({
                title: "Theme toggled",
                description: `Theme is now resolved as ${this.theme.resolvedTheme}.`,
            });
            return;
        }
        if (value === "toast-danger") {
            this.showDestructiveToast();
            return;
        }
        if (value === "open-preview") {
            this.announcePreviewRoute();
            return;
        }
        this.showToast();
    }

    updateFormatting(value) {
        this.form.formatting = Array.isArray(value) ? value : [];
    }
}
