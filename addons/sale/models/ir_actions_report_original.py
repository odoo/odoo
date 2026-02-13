# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
import subprocess
import tempfile
from odoo import models, api
from odoo.tools import config


class IrActionsReportOriginal(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, paperformat_id, landscape, specific_paperformat_args=None, set_viewport_size=False):
        """Override to add memory and resource management options - macOS compatible"""
        command_args = super()._build_wkhtmltopdf_args(paperformat_id, landscape, specific_paperformat_args, set_viewport_size)
        
        # Remove unsupported arguments first
        command_args = [arg for arg in command_args if not arg.startswith('--memory-limit')]
        command_args = [arg for arg in command_args if not arg.startswith('--timeout')]
        
        # Add only supported options for macOS
        command_args.extend([
            '--disable-local-file-access',
            '--quiet',
            '--no-pdf-compression',
            '--disable-smart-shrinking',
            '--print-media-type',
            '--no-stop-slow-scripts'
        ])
        
        # Add javascript delay based on system resources
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                command_args.extend(['--javascript-delay', '5000'])
            elif memory.percent > 60:
                command_args.extend(['--javascript-delay', '3000'])
            else:
                command_args.extend(['--javascript-delay', '1000'])
        except:
            command_args.extend(['--javascript-delay', '2000'])
        
        # Add performance optimizations based on system state
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 70:
                command_args.append('--no-images')
            if memory.percent > 85:
                command_args.append('--disable-javascript')
            if memory.percent > 75:
                command_args.append('--lowquality')
        except:
            pass
        
        return command_args

    def _run_wkhtmltopdf(self, bodies, header=None, footer=None, landscape=False, specific_paperformat_args=None, set_viewport_size=False, report_ref=False):
        """Override to handle memory issues and subprocess limits - macOS compatible"""
        try:
            # Set ulimit for file descriptors
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_NOFILE, (10000, 10000))
                resource.setrlimit(resource.RLIMIT_NPROC, (2048, 2048))
            except (ImportError, ValueError, OSError):
                pass
            
            # Use temporary files to reduce memory usage
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create temporary HTML files
                html_files = []
                for i, body in enumerate(bodies):
                    html_file = os.path.join(temp_dir, f'body_{i}.html')
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(body)
                    html_files.append(html_file)
                
                # Create temporary output file
                pdf_file = os.path.join(temp_dir, 'output.pdf')
                
                # Build command with memory management
                command_args = self._build_wkhtmltopdf_args(
                    self.get_paperformat(),
                    landscape,
                    specific_paperformat_args,
                    set_viewport_size
                )
                
                # Add input and output files
                command_args.extend(html_files + [pdf_file])
                
                # Run with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        result = subprocess.run(
                            ['wkhtmltopdf'] + command_args,
                            capture_output=True,
                            timeout=120,  # 2 minutes timeout
                            encoding='utf-8',
                            check=False
                        )
                        
                        if result.returncode != 0:
                            # Handle specific error codes
                            if result.returncode == -11:
                                if attempt < max_retries - 1:
                                    # Memory limit exceeded, try with reduced settings
                                    command_args = [arg for arg in command_args if not arg.startswith('--javascript-delay')]
                                    command_args.extend(['--javascript-delay', '10000', '--no-images', '--disable-javascript', '--lowquality'])
                                    continue
                                else:
                                    raise Exception("Wkhtmltopdf failed due to memory limit. Please reduce the report complexity or increase system memory.")
                            elif result.returncode == -9:
                                if attempt < max_retries - 1:
                                    # Process killed, try with minimal settings
                                    command_args = [
                                        '--disable-local-file-access',
                                        '--quiet',
                                        '--no-pdf-compression',
                                        '--disable-smart-shrinking',
                                        '--print-media-type',
                                        '--javascript-delay', '10000',
                                        '--no-images',
                                        '--disable-javascript',
                                        '--lowquality'
                                    ] + html_files + [pdf_file]
                                    continue
                                else:
                                    raise Exception("Wkhtmltopdf process was killed due to memory constraints.")
                            else:
                                raise Exception(f"Wkhtmltopdf failed with error code {result.returncode}: {result.stderr}")
                        
                        # Read the generated PDF
                        with open(pdf_file, 'rb') as f:
                            return f.read()
                            
                    except subprocess.TimeoutExpired:
                        if attempt < max_retries - 1:
                            continue
                        raise Exception("Wkhtmltopdf timeout exceeded. The report is too complex or system is overloaded.")
                    except FileNotFoundError:
                        raise Exception("Wkhtmltopdf binary not found. Please install wkhtmltopdf.")
                    except Exception as e:
                        if attempt < max_retries - 1:
                            continue
                        raise Exception(f"Wkhtmltopdf execution failed: {str(e)}")
                    
        except Exception as e:
            # Fallback to original method if our enhanced method fails
            return super()._run_wkhtmltopdf(bodies, header, footer, landscape, specific_paperformat_args, set_viewport_size, report_ref)
