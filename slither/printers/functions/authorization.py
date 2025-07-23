"""
    Module printing summary of the contract
"""
from typing import List

from slither.printers.abstract_printer import AbstractPrinter
from slither.core.declarations.function import Function
from slither.utils.myprettytable import MyPrettyTable
from slither.utils.output import Output

import csv
import os

class PrinterWrittenVariablesAndAuthorization(AbstractPrinter):

    ARGUMENT = "vars-and-auth"
    HELP = "Print the state variables written and the authorization of the functions"

    WIKI = "https://github.com/trailofbits/slither/wiki/Printer-documentation#variables-written-and-authorization"

    @staticmethod
    def get_msg_sender_checks(function: Function) -> List[str]:
        all_functions = (
            [
                ir.function
                for ir in function.all_internal_calls()
                if isinstance(ir.function, Function)
            ]
            + [function]
            + [m for m in function.modifiers if isinstance(m, Function)]
        )

        all_nodes_ = [f.nodes for f in all_functions]
        all_nodes = [item for sublist in all_nodes_ for item in sublist]

        all_conditional_nodes = [
            n for n in all_nodes if n.contains_if() or n.contains_require_or_assert()
        ]
        all_conditional_nodes_on_msg_sender = [
            str(n.expression)
            for n in all_conditional_nodes
            if "msg.sender" in [v.name for v in n.solidity_variables_read]
        ]
        return all_conditional_nodes_on_msg_sender

    def _export_to_csv(self, data, filename_prefix, export_dir):
        """Export data to CSV files"""
        for contract_name, state_vars_data, functions_data in data:
            # Export state variables
            state_vars_filename = os.path.join(export_dir, f"{filename_prefix}_{contract_name}_state_variables.csv")
            with open(state_vars_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Variable Name", "Type", "Visibility", "Location"])
                for row in state_vars_data:
                    writer.writerow(row)
            
            # Export functions
            functions_filename = os.path.join(export_dir, f"{filename_prefix}_{contract_name}_functions.csv")
            with open(functions_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Function", "State Variables Written", "Conditions on msg.sender"])
                for row in functions_data:
                    writer.writerow(row)
            
            print(f"CSV files exported: {state_vars_filename}, {functions_filename}")

    def _export_to_markdown(self, data, filename_prefix, export_dir):
        """Export data to Markdown files"""
        for contract_name, state_vars_data, functions_data in data:
            md_filename = os.path.join(export_dir, f"{filename_prefix}_{contract_name}.md")
            with open(md_filename, 'w', encoding='utf-8') as mdfile:
                mdfile.write(f"# Contract: {contract_name}\n\n")
                
                # State Variables section
                mdfile.write("## State Variables\n\n")
                mdfile.write("| Variable Name | Type | Visibility | Location |\n")
                mdfile.write("|---------------|------|------------|----------|\n")
                for row in state_vars_data:
                    escaped_row = [str(cell).replace('|', '\\|') for cell in row]
                    mdfile.write("| " + " | ".join(escaped_row) + " |\n")
                
                # Functions section
                mdfile.write("\n## Functions and State Variable Writes\n\n")
                mdfile.write("| Function | State Variables Written | Conditions on msg.sender |\n")
                mdfile.write("|----------|------------------------|-------------------------|\n")
                for row in functions_data:
                    escaped_row = [str(cell).replace('|', '\\|') for cell in row]
                    mdfile.write("| " + " | ".join(escaped_row) + " |\n")
            
            print(f"Markdown file exported: {md_filename}")

    def output(self, _filename: str) -> Output:
        """
        _filename is not used
        Args:
            _filename(string)
        """

        txt = ""
        all_tables = []
        export_data = []
        
        for contract in self.contracts:  # type: ignore
            txt += f"\nContract {contract.name}\n"
            
            # Output state variables
            txt += "\n=== State Variables ===\n"
            state_vars_table = MyPrettyTable(
                ["Variable Name", "Type", "Visibility", "Location"]
            )
            state_vars_data =[]
            for state_var in contract.state_variables:
                var_type = str(state_var.type) if state_var.type else "Unknown"
                visibility = state_var.visibility if hasattr(state_var, 'visibility') else "Unknown"
                location = state_var.location if hasattr(state_var, 'location') and state_var.location else "default"
                
                row_data = [
                    state_var.name,
                    var_type,
                    visibility,
                    location                   
                ]

                state_vars_table.add_row(row_data)
                state_vars_data.append(row_data)
            
            txt += str(state_vars_table) + "\n"
            all_tables.append((f"{contract.name}_state_variables", state_vars_table))
            
            # Output Functions and State Variables Writes
            txt += "\n=== Functions and State Variable Writes ===\n"
            functions_table = MyPrettyTable(
                ["Function", "State variables written", "Conditions on msg.sender"]
            )

            functions_data = []
            for function in contract.functions:
                state_variables_written = [
                    v.name for v in function.all_state_variables_written() if v.name
                ]
                msg_sender_condition = self.get_msg_sender_checks(function)

                row_data = [
                    function.name,
                    str(sorted(state_variables_written)),
                    str(sorted(msg_sender_condition)),
                ]
                
                functions_table.add_row(row_data)
                functions_data.append(row_data)
            
            txt += str(functions_table) + "\n"
            all_tables.append((f"{contract.name}_functions", functions_table))

            export_data.append((contract.name, state_vars_data, functions_data))

        # create export folder
        export_dir = "slither_export"
        os.makedirs(export_dir, exist_ok=True)

        # output to files 
        if _filename:
            base_name = os.path.splitext(os.path.basename(_filename))[0]
        else:
            base_name = "slither_vars_and_auth"

        # export to csv and markdown
        self._export_to_csv(export_data, base_name, export_dir)
        self._export_to_markdown(export_data, base_name, export_dir)

        print(f"\nAll files exported to: {os.path.abspath(export_dir)}/")

        self.info(txt)
        res = self.generate_output(txt)
        for name, table in all_tables:
            res.add_pretty_table(table, name)

        return res