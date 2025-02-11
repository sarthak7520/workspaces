import antlr4
from SystemVerilogLexer import SystemVerilogLexer
from SystemVerilogParser import SystemVerilogParser
from SystemVerilogParserListener import SystemVerilogParserListener
from antlr4.error.ErrorListener import ErrorListener
import os


class UVMComponentListener(SystemVerilogParserListener):
    MODULE = "module"
    INTERFACE = "interface"
    PROGRAM = "program"
    CLASS = "class"
    PACKAGE = "package"
    CHECKER = "checker"
    COVERGROUP = "covergroup"

    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.components = []

    def _add_component(self, component_type, identifier, ctx, details=None):
        if identifier:
            component = {
                "type": component_type,
                "name": identifier,
                "filename": self.filename,
                "line": ctx.start.line if hasattr(ctx, 'start') else 0
            }
            if details:
                component.update(details)  # Add extra details if provided
            self.components.append(component)

    def _extract_identifier(self, ctx, header_method, identifier_method, warning_message):
        """Extracts an identifier from a context, given the header and identifier methods."""
        if header_method(ctx):
            identifier_ctx = identifier_method(header_method(ctx))
            if identifier_ctx:
                return identifier_ctx.getText()
            else:
                print(f"Warning: {warning_message} but no identifier within it.")
        else:
            print(f"Warning: {warning_message} found.")
        return None

    def enterModule_declaration(self, ctx: SystemVerilogParser.Module_declarationContext):
        print("DEBUG: Found module declaration -", ctx.getText())
        module_identifier = self._extract_identifier(
            ctx,
            lambda c: c.module_header(),  # Use a lambda function here
            lambda header: header.module_identifier(),
            "Module declaration without a module_header"
        )
        ports = self.extract_ports(ctx)
        self._add_component(UVMComponentListener.MODULE, module_identifier, ctx, {"ports": ports})

    def enterInterface_declaration(self, ctx: SystemVerilogParser.Interface_declarationContext):
        print("DEBUG: Found interface declaration -", ctx.getText())
        interface_identifier = self._extract_identifier(
            ctx,
            lambda c: c.interface_header(),  # Use a lambda function here
            lambda header: header.interface_identifier(),
            "Interface declaration without an interface_header"
        )
        signals = self.extract_signals(ctx)
        modports = self.extract_modports(ctx)
        self._add_component(UVMComponentListener.INTERFACE, interface_identifier, ctx, {"signals": signals, "modports": modports})

    def enterProgram_declaration(self, ctx: SystemVerilogParser.Program_declarationContext):
        print("DEBUG: Found program declaration -", ctx.getText())
        program_identifier = self._extract_identifier(
            ctx,
            lambda c: c.program_header(),  # Use a lambda function here
            lambda header: header.program_identifier(),
            "Program declaration without a program_header"
        )
        self._add_component(UVMComponentListener.PROGRAM, program_identifier, ctx)

    def enterClass_declaration(self, ctx: SystemVerilogParser.Class_declarationContext):
        class_identifier = ctx.class_identifier().getText() if hasattr(ctx, 'class_identifier') and ctx.class_identifier() else None
        self._add_component(UVMComponentListener.CLASS, class_identifier, ctx)

    def enterPackage_declaration(self, ctx: SystemVerilogParser.Package_declarationContext):
        package_identifier = ctx.package_identifier().getText() if hasattr(ctx, 'package_identifier') and ctx.package_identifier() else None
        self._add_component(UVMComponentListener.PACKAGE, package_identifier, ctx)

    def enterChecker_declaration(self, ctx: SystemVerilogParser.Checker_declarationContext):
        checker_identifier = ctx.checker_identifier().getText() if hasattr(ctx, 'checker_identifier') and ctx.checker_identifier() else None
        self._add_component(UVMComponentListener.CHECKER, checker_identifier, ctx)

    def enterCovergroup_declaration(self, ctx: SystemVerilogParser.Covergroup_declarationContext):
        covergroup_identifier = ctx.covergroup_identifier().getText() if hasattr(ctx, 'covergroup_identifier') and ctx.covergroup_identifier() else None
        self._add_component(UVMComponentListener.COVERGROUP, covergroup_identifier, ctx)

    def extract_ports(self, ctx):
        """
        Extracts port declarations from a module context.
        Returns:
            list: A list of dictionaries, where each dictionary represents a port and
                contains its direction, name, and type.
        """
        ports = []
        # Extract all port declarations
        if ctx.module_header() and ctx.module_header().list_of_port_declarations():
            list_of_ports = ctx.module_header().list_of_port_declarations()
            if list_of_ports.port_decl():
                for port_decl_ctx in list_of_ports.port_decl():
                    if port_decl_ctx.ansi_port_declaration():
                        ansi_port = port_decl_ctx.ansi_port_declaration()
                        direction = ansi_port.port_direction().getText() if ansi_port.port_direction() else "inout"

                        # Extract the port name using a more robust approach
                        port_identifier = ansi_port.port_identifier()
                        port_name = port_identifier.getText() if port_identifier else ""

                        # Extract data type information
                        data_type = ""
                        if ansi_port.data_type():
                            data_type = ansi_port.data_type().getText()  # Get data type as text
                        elif ansi_port.implicit_data_type():
                            data_type = ansi_port.implicit_data_type().getText()  # Get implicit data type as text
                        ports.append({"direction": direction, "name": port_name, "type": data_type})

            elif list_of_ports.port():
                for port_ctx in list_of_ports.port():
                    if port_ctx.port_implicit():
                        port_implicit = port_ctx.port_implicit()
                        # Extract the port name using a more robust approach
                        if port_implicit.port_expression():
                            port_expression = port_implicit.port_expression()
                            port_identifier = port_expression.port_identifier()
                            port_name = port_identifier.getText() if port_identifier else ""
                            ports.append({"direction": "inout", "name": port_name, "type": ""})
            else:
                print("Warning: list_of_port_declarations found, but no port_decl or port within it.")
        return ports

    def extract_modports(self, ctx):
        """
        Extracts modport declarations from an interface context.
        Returns:
            list: A list of dictionaries, where each dictionary represents a modport and
                contains its name and a list of its ports with their directions.
        """
        modports = []
        # Extract modport definitions inside the interface
        for interface_item_ctx in ctx.interface_item():  # Iterate through interface items
            if interface_item_ctx:
                if interface_item_ctx.modport_declaration():
                    modport_ctx = interface_item_ctx.modport_declaration()
                    if modport_ctx:
                        # Ensure modport_identifier exists before accessing it
                        if modport_ctx.modport_identifier():
                            modport_name = modport_ctx.modport_identifier().getText()
                            port_decls = []

                            # Access modport_ports_declaration correctly (handling possible absence)
                            if modport_ctx.modport_ports_declaration():
                                for mp_ports_dec in modport_ctx.modport_ports_declaration():
                                    # Add a check for mp_ports_dec to ensure it's not None
                                    if mp_ports_dec:
                                        port_direction = mp_ports_dec.port_direction().getText() if mp_ports_dec.port_direction() else "inout"
                                        port_id = mp_ports_dec.port_identifier().getText()
                                        port_decls.append({"direction": port_direction, "name": port_id})
                            else:
                                print("Warning: modport_declaration has no modport_ports_declaration.")

                            modports.append({"name": modport_name, "ports": port_decls})
                        else:
                            print("Warning: modport_declaration found, but no modport_identifier within it.")

        return modports

    def extract_signals(self, ctx):
        """
        Extracts signal declarations from an interface context.
        Returns:
            list: A list of dictionaries, where each dictionary represents a signal and
                contains its type and name.
        """
        signals = []
        # Extract all signal declarations
        for item in ctx.interface_item():  # get all interface items
            if item.module_common_item():  # drill down
                module_item = item.module_common_item()
                if module_item.module_item_declaration():
                    module_item_decl = module_item.module_item_declaration()
                    if hasattr(module_item_decl, 'data_declaration') and module_item_decl.data_declaration():
                        data_decl = module_item_decl.data_declaration()
                        data_type = data_decl.data_type().getText() if data_decl.data_type() else "logic"
                        list_of_vars = data_decl.list_of_variable_decl_assignments()
                        if list_of_vars:
                            for var in list_of_vars.variable_decl_assignment():
                                var_name = var.variable_identifier().getText() if var.variable_identifier() else ""
                                signals.append({"type": data_type, "name": var_name})
        return signals


    def get_components(self):
        return self.components

