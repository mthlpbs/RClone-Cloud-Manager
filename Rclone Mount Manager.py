#!/usr/bin/env python3
"""
Rclone Mount Manager - A utility to manage mounting and unmounting of rclone drives
"""
import os
import subprocess
import sys
import threading
import time
from typing import Dict, List

# Import Rich library components for better UI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich import print as rprint
from rich.live import Live

# Initialize Rich console
console = Console()

# Define class for managing rclone operations
class RcloneMountManager:
    def __init__(self):
        self.mounted_drives: Dict[str, Dict] = {}
        self.mounting_process = None
        self.mount_thread = None
        self.running = True
        self.current_mount_name = None

    def get_rclone_remotes(self) -> List[str]:
        """Get list of configured rclone remotes"""
        try:
            result = subprocess.run(
                ["rclone", "listremotes"], 
                capture_output=True, 
                text=True,
                check=True
            )
            # Remove the colon at the end of each remote name
            remotes = [remote.strip() for remote in result.stdout.splitlines()]
            return remotes
        except subprocess.CalledProcessError:
            console.print("[bold red]Error retrieving rclone remotes. Is rclone installed?[/bold red]")
            return []
        except FileNotFoundError:
            console.print("[bold red]Error: rclone command not found. Please install rclone first.[/bold red]")
            return []

    def mount_drive(self, remote: str, mount_point: str) -> bool:
        """
        Mount a remote drive using rclone with the specified parameters
        """
        try:
            # Stop any previous mount process
            self.stop_current_mount()
            
            # Prepare mounting command
            mount_cmd = [
                "rclone", "mount", 
                remote, mount_point,
                "--vfs-cache-mode", "full", 
                "--vfs-cache-max-size", "10G", 
                "--vfs-cache-max-age", "1h", 
                "--buffer-size", "64M", 
                "--dir-cache-time", "72h", 
                "--poll-interval", "15s", 
                "--timeout", "1m", 
                "--log-level", "INFO"
            ]
            
            # Start the mount process
            self.current_mount_name = remote
            self.mounting_process = subprocess.Popen(
                mount_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store mount information
            self.mounted_drives[remote] = {
                "mount_point": mount_point,
                "process": self.mounting_process
            }
            
            # Return success if process started
            return True
        except Exception as e:
            console.print(f"[bold red]Error mounting drive: {e}[/bold red]")
            return False

    def unmount_drive(self, remote: str) -> bool:
        """Unmount a previously mounted drive"""
        if remote in self.mounted_drives:
            mount_info = self.mounted_drives[remote]
            
            try:
                # Kill the mounting process
                if mount_info["process"] and mount_info["process"].poll() is None:
                    mount_info["process"].terminate()
                    mount_info["process"].wait(timeout=5)
                
                # On Windows, use "taskkill" to ensure all rclone processes are terminated
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/IM", "rclone.exe"], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL)
                
                # Remove the drive from the mounted_drives dict
                del self.mounted_drives[remote]
                return True
            except Exception as e:
                console.print(f"[bold red]Error unmounting drive: {e}[/bold red]")
                return False
        
        console.print(f"[bold yellow]Warning: Drive {remote} is not mounted or was already unmounted.[/bold yellow]")
        return False

    def stop_current_mount(self):
        """Stop the current mount process if any"""
        if self.current_mount_name and self.current_mount_name in self.mounted_drives:
            self.unmount_drive(self.current_mount_name)
            self.current_mount_name = None

    def is_drive_mounted(self, remote: str) -> bool:
        """Check if a drive is currently mounted"""
        return remote in self.mounted_drives

    def get_mounted_drives(self) -> List[str]:
        """Get list of currently mounted drives"""
        return list(self.mounted_drives.keys())

# UI Class to manage the interface
class MountManagerUI:
    def __init__(self):
        self.manager = RcloneMountManager()
        self.console = Console()
    
    def display_header(self):
        """Display the application header"""
        self.console.print(Panel.fit(
            "[bold blue]Rclone Mount Manager[/bold blue]",
            subtitle="[italic]Manage your cloud drives easily[/italic]"
        ))
    
    def list_remotes(self) -> List[str]:
        """Get and display the list of available remotes"""
        remotes = self.manager.get_rclone_remotes()
        
        if not remotes:
            self.console.print("[yellow]No remotes found. Please configure rclone first.[/yellow]")
            return []
        
        table = Table(title="Available Cloud Drives")
        table.add_column("Number", justify="right", style="cyan", no_wrap=True)
        table.add_column("Remote Name", style="green")
        table.add_column("Status", style="magenta")
        
        for i, remote in enumerate(remotes, 1):
            status = "[green]MOUNTED[/green]" if self.manager.is_drive_mounted(remote) else "[gray]Not Mounted[/gray]"
            table.add_row(str(i), remote, status)
        
        self.console.print(table)
        return remotes

    def mount_menu(self):
        """Show the mount menu and handle drive mounting"""
        while True:
            self.display_header()
            remotes = self.list_remotes()
            
            if not remotes:
                if Confirm.ask("Would you like to return to the main menu?"):
                    return
                else:
                    sys.exit(0)
            
            self.console.print("\n[bold cyan]Options:[/bold cyan]")
            self.console.print("  [yellow]1-{0}[/yellow]: Select a drive to mount".format(len(remotes)))
            self.console.print("  [yellow]b[/yellow]: Back to main menu")
            self.console.print("  [yellow]q[/yellow]: Quit")
            
            choice = Prompt.ask("\nEnter your choice", 
                               choices=[str(i) for i in range(1, len(remotes)+1)] + ['b', 'q'])
            
            if choice == 'q':
                sys.exit(0)
            elif choice == 'b':
                return
            else:
                try:
                    selected_idx = int(choice) - 1
                    selected_remote = remotes[selected_idx]
                    self._handle_mount(selected_remote)
                except (ValueError, IndexError):
                    self.console.print("[bold red]Invalid selection. Please try again.[/bold red]")
                    time.sleep(1)

    def _handle_mount(self, remote: str):
        """Handle the mounting of a selected remote"""
        self.console.clear()
        self.display_header()
        
        # Check if drive is already mounted
        if self.manager.is_drive_mounted(remote):
            self.console.print(f"[yellow]{remote} is already mounted.[/yellow]")
            if Confirm.ask("Would you like to unmount it?"):
                if self.manager.unmount_drive(remote):
                    self.console.print(f"[green]{remote} successfully unmounted.[/green]")
                time.sleep(1)
            return
        
        # For Windows, use drive letters
        if os.name == 'nt':
            available_drives = self._get_available_drive_letters()
            if not available_drives:
                self.console.print("[bold red]No drive letters available for mounting.[/bold red]")
                time.sleep(2)
                return
                
            mount_point = Prompt.ask(
                "Select drive letter to use for mounting", 
                choices=available_drives
            )
            # Add colon for Windows drive letter
            mount_point = f"{mount_point}:"
        else:
            # For Unix-like systems
            mount_point = Prompt.ask("Enter mount point (directory path)")
            # Ensure directory exists
            os.makedirs(mount_point, exist_ok=True)
        
        with self.console.status(f"[bold green]Mounting {remote} to {mount_point}...[/bold green]"):
            success = self.manager.mount_drive(remote, mount_point)
        
        if success:
            self.console.print(f"[bold green]Successfully mounted {remote} to {mount_point}[/bold green]")
            
            # Display monitor screen
            self._monitor_mounted_drive(remote, mount_point)
        else:
            self.console.print("[bold red]Failed to mount the drive.[/bold red]")
            time.sleep(1)
    
    def _monitor_mounted_drive(self, remote: str, mount_point: str):
        """Monitor a mounted drive and provide option to unmount"""
        with Live(refresh_per_second=4) as live:
            while self.manager.is_drive_mounted(remote):
                # Create status display
                status_panel = Panel(
                    f"[bold green]{remote}[/bold green] is mounted to [bold yellow]{mount_point}[/bold yellow]\n\n"
                    "[bold cyan]Press 'q' to unmount | Press 'b' to return to menu[/bold cyan]",
                    title="Drive Monitor",
                    border_style="green"
                )
                
                live.update(status_panel)
                
                # Check for keypress
                if os.name == 'nt':
                    # Windows-specific keyboard input
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        if key == 'q':
                            self.manager.unmount_drive(remote)
                            self.console.print(f"[bold green]{remote} successfully unmounted.[/bold green]")
                            time.sleep(1)
                            break
                        elif key == 'b':
                            break
                else:
                    # Unix-like keyboard input (simplified version)
                    import select
                    import tty
                    import termios
                    
                    fd = sys.stdin.fileno()
                    old_settings = termios.tcgetattr(fd)
                    try:
                        tty.setraw(sys.stdin.fileno())
                        if select.select([sys.stdin], [], [], 0.5)[0]:
                            key = sys.stdin.read(1).lower()
                            if key == 'q':
                                self.manager.unmount_drive(remote)
                                self.console.print(f"[bold green]{remote} successfully unmounted.[/bold green]")
                                time.sleep(1)
                                break
                            elif key == 'b':
                                break
                    finally:
                        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
                time.sleep(0.5)
                
    def _get_available_drive_letters(self) -> List[str]:
        """Get list of available drive letters on Windows"""
        if os.name != 'nt':
            return []
            
        used_drives = []
        for letter in range(ord('A'), ord('Z') + 1):
            drive_letter = chr(letter)
            if os.path.exists(f"{drive_letter}:"):
                used_drives.append(drive_letter)
                
        available_drives = [chr(letter) for letter in range(ord('A'), ord('Z') + 1) 
                            if chr(letter) not in used_drives]
        return available_drives

    def unmount_menu(self):
        """Show a menu of mounted drives to unmount"""
        self.display_header()
        
        # Get currently mounted drives
        mounted_drives = self.manager.get_mounted_drives()
        
        if not mounted_drives:
            self.console.print("[yellow]No drives are currently mounted.[/yellow]")
            time.sleep(1)
            return
            
        # Show table of mounted drives
        table = Table(title="Currently Mounted Drives")
        table.add_column("Number", justify="right", style="cyan", no_wrap=True)
        table.add_column("Remote Name", style="green")
        table.add_column("Mount Point", style="blue")
        
        for i, remote in enumerate(mounted_drives, 1):
            mount_info = self.manager.mounted_drives[remote]
            table.add_row(str(i), remote, mount_info["mount_point"])
        
        self.console.print(table)
        
        # Provide options
        self.console.print("\n[bold cyan]Options:[/bold cyan]")
        self.console.print("  [yellow]1-{0}[/yellow]: Select a drive to unmount".format(len(mounted_drives)))
        self.console.print("  [yellow]b[/yellow]: Back to main menu")
        
        choice = Prompt.ask("\nEnter your choice", 
                           choices=[str(i) for i in range(1, len(mounted_drives)+1)] + ['b'])
        
        if choice == 'b':
            return
        else:
            try:
                selected_idx = int(choice) - 1
                selected_remote = mounted_drives[selected_idx]
                
                if self.manager.unmount_drive(selected_remote):
                    self.console.print(f"[bold green]{selected_remote} successfully unmounted.[/bold green]")
                else:
                    self.console.print(f"[bold red]Failed to unmount {selected_remote}.[/bold red]")
                    
                time.sleep(1)
            except (ValueError, IndexError):
                self.console.print("[bold red]Invalid selection. Please try again.[/bold red]")
                time.sleep(1)

    def main_menu(self):
        """Display the main menu"""
        while True:
            self.console.clear()
            self.display_header()
            
            # Show main options
            options = [
                "[1] Mount a cloud drive",
                "[2] Unmount a cloud drive",
                "[3] View mounted drives",
                "[q] Exit program"
            ]
            
            for option in options:
                self.console.print(f"  {option}")
                
            choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "3", "q"])
            
            if choice == "1":
                self.mount_menu()
            elif choice == "2":
                self.unmount_menu()
            elif choice == "3":
                self._view_mounted_drives()
            elif choice == "q":
                # Ensure all drives are unmounted before exit
                self._cleanup_before_exit()
                self.console.print("[bold green]Exiting...[/bold green]")
                break
    
    def _view_mounted_drives(self):
        """View currently mounted drives"""
        self.display_header()
        
        mounted_drives = self.manager.get_mounted_drives()
        
        if not mounted_drives:
            self.console.print("[yellow]No drives are currently mounted.[/yellow]")
        else:
            table = Table(title="Currently Mounted Drives")
            table.add_column("Remote Name", style="green")
            table.add_column("Mount Point", style="blue")
            
            for remote in mounted_drives:
                mount_info = self.manager.mounted_drives[remote]
                table.add_row(remote, mount_info["mount_point"])
            
            self.console.print(table)
        
        input("\nPress Enter to continue...")
    
    def _cleanup_before_exit(self):
        """Clean up any mounted drives before exiting"""
        mounted_drives = self.manager.get_mounted_drives().copy()
        
        if mounted_drives:
            self.console.print("[yellow]Unmounting drives before exit...[/yellow]")
            
            for remote in mounted_drives:
                self.manager.unmount_drive(remote)
                
            self.console.print("[green]All drives unmounted successfully.[/green]")

# Main entry point
if __name__ == "__main__":
    try:
        # Check if rclone is installed
        try:
            subprocess.run(["rclone", "--version"], 
                          capture_output=True, 
                          check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            console = Console()
            console.print("[bold red]Error: rclone is not installed or not in your PATH.[/bold red]")
            console.print("Please install rclone from https://rclone.org/downloads/ and try again.")
            sys.exit(1)
            
        # Start the UI
        ui = MountManagerUI()
        ui.main_menu()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Program terminated by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
        sys.exit(1)