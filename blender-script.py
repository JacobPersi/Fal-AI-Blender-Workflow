bl_info = {
    "name": "FAL Package Manager",
    "author": "Claude",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > FAL",
    "description": "Manages FAL package installation and API key",
    "category": "3D View",
}

import bpy
import os
import subprocess
import sys
import threading
import site
import tempfile
import time


# Setup logging
def log_debug(message):
    """Log debug messages to console and store in scene property"""
    print(f"[FAL_DEBUG] {message}")
    # Store in scene property if available
    try:
        if hasattr(bpy.context.scene, "fal_debug_log"):
            current_log = bpy.context.scene.fal_debug_log
            bpy.context.scene.fal_debug_log = f"{current_log}\n[DEBUG] {message}"
    except:
        pass


def log_info(message):
    """Log info messages to console, UI, and store in scene property"""
    print(f"[FAL_INFO] {message}")
    # Store in scene property if available
    try:
        if hasattr(bpy.context.scene, "fal_debug_log"):
            current_log = bpy.context.scene.fal_debug_log
            bpy.context.scene.fal_debug_log = f"{current_log}\n[INFO] {message}"
    except:
        pass
    # Update UI message if available
    try:
        bpy.context.scene.fal_status_message = message
    except:
        pass


def log_error(message):
    """Log error messages to console, UI, and store in scene property"""
    print(f"[FAL_ERROR] {message}")
    # Store in scene property if available
    try:
        if hasattr(bpy.context.scene, "fal_debug_log"):
            current_log = bpy.context.scene.fal_debug_log
            bpy.context.scene.fal_debug_log = f"{current_log}\n[ERROR] {message}"
    except:
        pass
    # Update UI message if available
    try:
        bpy.context.scene.fal_status_message = f"ERROR: {message}"
    except:
        pass


class FALPackageChecker:
    @staticmethod
    def is_package_installed():
        """Check if fal package is installed in Blender's Python environment."""
        log_debug("Checking if fal package is installed...")
        try:
            import fal
            log_debug(f"FAL package found: {fal.__file__}")
            return True
        except ImportError as e:
            log_debug(f"FAL package not found: {str(e)}")
            return False
    
    @staticmethod
    def install_package():
        """Start installation in a monitoring thread."""
        log_debug("Starting FAL package installation process")
        
        # Reset progress indicators
        bpy.context.scene.fal_install_progress = 0
        bpy.context.scene.fal_install_in_progress = True
        bpy.context.scene.fal_install_log = ""
        bpy.context.scene.fal_install_success = False
        
        # Start the installation thread
        install_thread = threading.Thread(target=FALPackageChecker._install_process)
        install_thread.daemon = True
        install_thread.start()
        
        # Start the monitoring timer
        if not bpy.app.timers.is_registered(FALPackageChecker._monitor_installation):
            bpy.app.timers.register(FALPackageChecker._monitor_installation, first_interval=0.5)
            
        log_info("Installing FAL package... This may take a moment.")
        return install_thread
    
    @staticmethod
    def _install_process():
        """Actual installation process running in a separate thread."""
        log_debug("Installation thread started")
        
        # Use a temporary file to capture pip's output
        with tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.txt') as temp_file:
            log_path = temp_file.name
            log_debug(f"Created temporary log file: {log_path}")
        
        site_packages = site.getsitepackages()[0]
        python_exe = sys.executable
        
        log_debug(f"Using Python executable: {python_exe}")
        log_debug(f"Installing to site-packages: {site_packages}")
        
        # Install package directly to Blender's site-packages
        cmd = [python_exe, "-m", "pip", "install", "fal", "--target", site_packages, "--verbose"]
        log_debug(f"Running command: {' '.join(cmd)}")
        
        try:
            # Redirect both stdout and stderr to our log file
            with open(log_path, 'w') as log_file:
                process = subprocess.Popen(
                    cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                # Store the process for monitoring
                bpy.context.scene.fal_install_pid = process.pid
                log_debug(f"Started pip process with PID: {process.pid}")
                
                # Wait for process to complete
                process.wait()
                log_debug(f"Pip process completed with return code: {process.returncode}")
            
            # Check if installation was successful
            success = process.returncode == 0
            
            # Read the output
            with open(log_path, 'r') as log_file:
                output = log_file.read()
                log_debug(f"Captured {len(output)} bytes of log output")
            
            # Store the results
            bpy.context.scene.fal_install_log = output
            bpy.context.scene.fal_install_success = success
            
            if success:
                log_info("FAL package installation completed successfully!")
            else:
                log_error(f"FAL package installation failed with code {process.returncode}")
                
        except Exception as e:
            error_msg = f"Exception during installation: {str(e)}"
            log_error(error_msg)
            bpy.context.scene.fal_install_log = error_msg
            bpy.context.scene.fal_install_success = False
        
        # Mark installation as complete
        bpy.context.scene.fal_install_in_progress = False
        bpy.context.scene.fal_install_progress = 100 if bpy.context.scene.fal_install_success else 0
        
        # Clean up temp file after a delay
        try:
            time.sleep(1)  # Make sure file is not in use
            os.unlink(log_path)
            log_debug(f"Removed temporary log file: {log_path}")
        except Exception as e:
            log_debug(f"Failed to remove temp file: {str(e)}")
    
    @staticmethod
    def _monitor_installation():
        """Timer callback to update the UI during installation."""
        if not bpy.context.scene.fal_install_in_progress:
            log_debug("Installation monitoring complete")
            # Force redraw all VIEW_3D areas
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            return None  # Stop the timer
        
        # Update progress (simulated incremental progress)
        current_progress = bpy.context.scene.fal_install_progress
        if current_progress < 90:  # Reserve 90-100 for completion
            bpy.context.scene.fal_install_progress += 1
        
        # Force redraw all VIEW_3D areas
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        
        return 0.2  # Continue the timer with 0.2 second interval


# Addon preferences to store API key
class FALAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    api_key: bpy.props.StringProperty(
        name="FAL API Key",
        description="API Key for FAL service",
        default="",
        subtype='PASSWORD'
    )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "api_key")
        layout.label(text="Changes to this key will be applied when you save user preferences")


def get_api_key():
    """Get API key from addon preferences, then fall back to environment variable"""
    log_debug("Getting API key")
    # First try to get from addon preferences
    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
        if prefs.api_key:
            log_debug("API key found in addon preferences")
            return prefs.api_key
    except (KeyError, AttributeError) as e:
        log_debug(f"Could not get API key from preferences: {str(e)}")
    
    # Fall back to environment variable
    try:
        key = os.environ.get("FAL_KEY", "")
        if key:
            log_debug("API key found in environment variable")
        else:
            log_debug("No API key found in environment variable")
        return key
    except Exception as e:
        log_debug(f"Error accessing environment variable: {str(e)}")
        return ""


def set_api_key(value):
    """Set API key in both addon preferences and environment variable"""
    log_debug("Setting API key")
    # Save to addon preferences
    try:
        prefs = bpy.context.preferences.addons[__name__].preferences
        prefs.api_key = value
        log_debug("API key saved to addon preferences")
    except (KeyError, AttributeError) as e:
        log_debug(f"Could not save API key to preferences: {str(e)}")
    
    # Also set environment variable for current session
    try:
        os.environ["FAL_KEY"] = value
        log_debug("API key set as environment variable")
    except Exception as e:
        log_error(f"Error setting FAL_KEY environment variable: {e}")
        return False
    
    return True


class FAL_PT_Panel(bpy.types.Panel):
    """FAL Package Manager Panel"""
    bl_label = "FAL Package Manager"
    bl_idname = "FAL_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FAL'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Status message display
        if hasattr(scene, "fal_status_message") and scene.fal_status_message:
            layout.label(text=scene.fal_status_message)
        
        # Check if fal is installed
        is_fal_installed = FALPackageChecker.is_package_installed()
        
        # Display installation status
        box = layout.box()
        if is_fal_installed:
            box.label(text="✓ FAL package is installed", icon='CHECKMARK')
        else:
            box.label(text="✗ FAL package is not installed", icon='CANCEL')
            
            # If installation is in progress, show progress bar
            if hasattr(scene, "fal_install_in_progress") and scene.fal_install_in_progress:
                progress = scene.fal_install_progress
                box.label(text=f"Installation in progress: {progress}%")
                
                # Custom progress bar
                progress_bar = box.row()
                progress_bar.scale_y = 0.5
                progress_bar.prop(scene, "fal_install_progress", text="", slider=True)
                
            else:
                # Show install button if not in progress
                box.operator("fal.install_package", text="Install FAL Package")
        
        # Always show log buttons in a new box, regardless of installation status
        log_box = layout.box()
        log_box.label(text="Logs:", icon='TEXT')
        
        # Installation status display (if available)
        if hasattr(scene, "fal_install_success") and (hasattr(scene, "fal_install_log") and scene.fal_install_log):
            icon = 'CHECKMARK' if scene.fal_install_success else 'ERROR'
            status = "Success" if scene.fal_install_success else "Failed"
            log_box.label(text=f"Last installation: {status}", icon=icon)
        
        # Always show log buttons
        row = log_box.row()
        row.operator("fal.view_log", text="View Full Log")
        row.operator("fal.view_debug_log", text="View Debug Log")
        
        # FAL API Key management
        layout.separator()
        layout.label(text="FAL API Key Settings:")
        
        # Get current FAL_KEY value
        current_key = get_api_key()
        
        # Initialize scene property if needed
        if not hasattr(scene, "fal_api_key_input"):
            scene.fal_api_key_input = current_key
        
        # Display API key field (hidden as password)
        row = layout.row()
        row.prop(scene, "fal_api_key_input", text="FAL_KEY")
        
        # Update API key button
        layout.operator("fal.update_api_key", text="Update API Key")
        
        # Status message for the key
        if current_key:
            layout.label(text="API Key is set", icon='CHECKMARK')
        else:
            layout.label(text="No API Key detected", icon='ERROR')


class FAL_OT_InstallPackage(bpy.types.Operator):
    """Install FAL package using pip"""
    bl_idname = "fal.install_package"
    bl_label = "Install FAL Package"
    
    def execute(self, context):
        log_debug("Install package operator executed")
        
        if hasattr(context.scene, "fal_install_in_progress") and context.scene.fal_install_in_progress:
            self.report({'WARNING'}, "Installation already in progress")
            log_info("Installation already in progress")
            return {'CANCELLED'}
        
        self.report({'INFO'}, "Installing FAL package... This may take a moment.")
        FALPackageChecker.install_package()
        
        return {'FINISHED'}


class FAL_OT_ViewLog(bpy.types.Operator):
    """View the full installation log"""
    bl_idname = "fal.view_log"
    bl_label = "View Installation Log"
    
    def execute(self, context):
        log_debug("View log operator executed")
        
        # Create a text datablock to show the log
        log_text = bpy.data.texts.new("FAL_Installation_Log.txt")
        
        # Handle the case when no installation has occurred yet
        if hasattr(context.scene, "fal_install_log") and context.scene.fal_install_log:
            log_content = context.scene.fal_install_log
        else:
            log_content = "No installation log available yet. Install the FAL package first."
        
        log_text.write(log_content)
        
        # Open a text editor area and show the log
        self._show_text_in_editor(log_text)
        
        return {'FINISHED'}
    
    def _show_text_in_editor(self, text_datablock):
        """Helper to show text in editor"""
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.spaces.active.text = text_datablock
                    log_debug("Showing log in existing text editor")
                    return
        
        # If no text editor is open, try to open one in a new window
        try:
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'TEXT_EDITOR':
                        area.spaces.active.text = text_datablock
                        log_debug("Showing log in new text editor window")
                        return
        except:
            log_debug("Could not open new window, falling back to area change")
            
            # Fall back to changing an existing area
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.type = 'TEXT_EDITOR'
                        area.spaces.active.text = text_datablock
                        log_debug("Changed 3D view to text editor to show log")
                        return


class FAL_OT_ViewDebugLog(bpy.types.Operator):
    """View the debug log"""
    bl_idname = "fal.view_debug_log"
    bl_label = "View Debug Log"
    
    def execute(self, context):
        log_debug("View debug log operator executed")
        
        # Create a text datablock to show the debug log
        log_text = bpy.data.texts.new("FAL_Debug_Log.txt")
        
        # Handle the case when debug log is not available
        if hasattr(context.scene, "fal_debug_log") and context.scene.fal_debug_log:
            log_content = context.scene.fal_debug_log
        else:
            log_content = "No debug log available."
        
        log_text.write(log_content)
        
        # Open a text editor area and show the log
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    area.spaces.active.text = log_text
                    break
            else:
                # If no text editor is open, change the current area
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.type = 'TEXT_EDITOR'
                        area.spaces.active.text = log_text
                        break
        
        return {'FINISHED'}


class FAL_OT_UpdateAPIKey(bpy.types.Operator):
    """Update FAL API Key in environment variables"""
    bl_idname = "fal.update_api_key"
    bl_label = "Update FAL API Key"
    
    def execute(self, context):
        log_debug("Update API key operator executed")
        
        new_key = context.scene.fal_api_key_input
        log_debug(f"Updating API key (length: {len(new_key)})")
        
        if set_api_key(new_key):
            self.report({'INFO'}, "FAL API Key updated successfully")
            log_info("FAL API Key updated successfully")
        else:
            self.report({'ERROR'}, "Failed to update FAL API Key")
            log_error("Failed to update FAL API Key")
        
        return {'FINISHED'}


# Register and unregister functions
def register():
    log_debug("Registering FAL Package Manager addon")
    
    # Register properties
    bpy.types.Scene.fal_api_key_input = bpy.props.StringProperty(
        name="FAL API Key",
        description="API Key for FAL service",
        default="",
        subtype='PASSWORD'  # This hides the text as dots
    )
    
    bpy.types.Scene.fal_install_log = bpy.props.StringProperty(
        name="Installation Log",
        default=""
    )
    
    bpy.types.Scene.fal_debug_log = bpy.props.StringProperty(
        name="Debug Log",
        default="[DEBUG] FAL Package Manager debug log initialized"
    )
    
    bpy.types.Scene.fal_install_success = bpy.props.BoolProperty(
        name="Installation Success",
        default=False
    )
    
    bpy.types.Scene.fal_install_in_progress = bpy.props.BoolProperty(
        name="Installation In Progress",
        default=False
    )
    
    bpy.types.Scene.fal_install_progress = bpy.props.IntProperty(
        name="Installation Progress",
        default=0,
        min=0,
        max=100,
        subtype='PERCENTAGE'
    )
    
    bpy.types.Scene.fal_install_pid = bpy.props.IntProperty(
        name="Installation Process ID",
        default=-1
    )
    
    bpy.types.Scene.fal_status_message = bpy.props.StringProperty(
        name="Status Message",
        default=""
    )
    
    # Register classes
    for cls in (FALAddonPreferences, FAL_PT_Panel, FAL_OT_InstallPackage, 
                FAL_OT_UpdateAPIKey, FAL_OT_ViewLog, FAL_OT_ViewDebugLog):
        log_debug(f"Registering class: {cls.__name__}")
        bpy.utils.register_class(cls)
    
    log_debug("FAL Package Manager addon registration complete")


def unregister():
    log_debug("Unregistering FAL Package Manager addon")
    
    # Unregister classes
    for cls in (FAL_OT_ViewDebugLog, FAL_OT_ViewLog, FAL_OT_UpdateAPIKey, 
                FAL_OT_InstallPackage, FAL_PT_Panel, FALAddonPreferences):
        log_debug(f"Unregistering class: {cls.__name__}")
        bpy.utils.unregister_class(cls)
    
    # Unregister properties
    del bpy.types.Scene.fal_api_key_input
    del bpy.types.Scene.fal_install_log
    del bpy.types.Scene.fal_debug_log
    del bpy.types.Scene.fal_install_success
    del bpy.types.Scene.fal_install_in_progress
    del bpy.types.Scene.fal_install_progress
    del bpy.types.Scene.fal_install_pid
    del bpy.types.Scene.fal_status_message
    
    log_debug("FAL Package Manager addon unregistration complete")


if __name__ == "__main__":
    register()