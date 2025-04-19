bl_info = {
    "name": "FAL AI Image to 3D",
    "author": "Claude",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > FAL AI",
    "description": "Generate AI images and convert them to 3D meshes using FAL AI",
    "category": "3D View",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
}

import bpy
import os
import subprocess
import sys
import threading
import site
import tempfile
import time
import json
import requests
import fal.apps
from pathlib import Path
import bpy.utils.previews
import bmesh


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


class FALMeshProcessor:
    @staticmethod
    def process_mesh(obj):
        """Process the mesh with cleanup operations"""
        if obj.type != 'MESH':
            return
        
        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Get the bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Merge vertices by distance
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        
        # Update the mesh
        bmesh.update_edit_mesh(obj.data)
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Set origin to bottom center
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        # Move to ground plane
        obj.location.z = 0


class FALImageGenPreferences(bpy.types.PropertyGroup):
    save_directory: bpy.props.StringProperty(
        name="Save Directory",
        description="Directory to save generated images",
        default="",
        subtype='DIR_PATH'
    )
    
    prompt: bpy.props.StringProperty(
        name="Prompt",
        description="Text prompt for image generation",
        default=""
    )
    
    negative_prompt: bpy.props.StringProperty(
        name="Negative Prompt",
        description="Negative prompt for image generation",
        default=""
    )
    
    image_width: bpy.props.IntProperty(
        name="Width",
        description="Generated image width",
        default=1024,
        min=512,
        max=2048
    )
    
    image_height: bpy.props.IntProperty(
        name="Height", 
        description="Generated image height",
        default=1024,
        min=512,
        max=2048
    )
    
    num_inference_steps: bpy.props.IntProperty(
        name="Steps",
        description="Number of inference steps",
        default=28,
        min=1,
        max=100
    )
    
    enable_safety_checker: bpy.props.BoolProperty(
        name="Enable Safety Checker",
        description="Enable content safety checking",
        default=True
    )
    
    merge_distance: bpy.props.FloatProperty(
        name="Merge Distance",
        description="Distance for merging vertices",
        default=0.0001,
        min=0.00001,
        max=0.1
    )


class FAL_PT_MainPanel(bpy.types.Panel):
    """Main FAL AI Panel"""
    bl_label = "FAL AI Image to 3D"
    bl_idname = "FAL_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FAL AI'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = context.preferences.addons[__name__].preferences
        
        # Package installation section
        if not FALPackageChecker.is_package_installed():
            layout.label(text="FAL package not installed", icon='ERROR')
            layout.operator("fal.install_package", text="Install FAL Package")
            return
        
        # API key section
        if not get_api_key():
            layout.label(text="API key not set", icon='ERROR')
            layout.operator("fal.update_api_key", text="Set API Key")
            return
        
        # Image generation settings
        box = layout.box()
        box.label(text="Image Generation Settings", icon='IMAGE_DATA')
        
        box.prop(scene.fal_image_gen, "prompt")
        box.prop(scene.fal_image_gen, "negative_prompt")
        box.prop(scene.fal_image_gen, "image_width")
        box.prop(scene.fal_image_gen, "image_height")
        box.prop(scene.fal_image_gen, "num_inference_steps")
        box.prop(scene.fal_image_gen, "enable_safety_checker")
        
        # Mesh processing settings
        box = layout.box()
        box.label(text="Mesh Processing", icon='MESH_DATA')
        box.prop(scene.fal_image_gen, "merge_distance")
        
        # Generate button
        layout.operator("fal.generate_image", text="Generate Image and Convert to 3D")


class FAL_OT_GenerateImage(bpy.types.Operator):
    """Generate image using FAL API and convert to 3D mesh"""
    bl_idname = "fal.generate_image"
    bl_label = "Generate Image and Convert to 3D"
    
    def execute(self, context):
        scene = context.scene
        prefs = scene.fal_image_gen
        
        # Generate image
        try:
            image_path = self._generate_image(prefs)
            if not image_path:
                return {'CANCELLED'}
            
            # Create image plane
            obj = self.create_image_plane(context, image_path)
            
            # Process mesh
            FALMeshProcessor.process_mesh(obj)
            
            return {'FINISHED'}
        except Exception as e:
            log_error(f"Error during image generation and processing: {str(e)}")
            return {'CANCELLED'}


def register():
    """Register the addon and all its classes"""
    log_debug("Registering FAL AI Image to 3D addon")
    
    # Register properties
    bpy.types.Scene.fal_api_key_input = bpy.props.StringProperty(
        name="FAL API Key",
        description="API Key for FAL service",
        default="",
        subtype='PASSWORD'
    )
    
    bpy.types.Scene.fal_install_log = bpy.props.StringProperty(
        name="Installation Log",
        default=""
    )
    
    bpy.types.Scene.fal_debug_log = bpy.props.StringProperty(
        name="Debug Log",
        default="[DEBUG] FAL AI Image to 3D debug log initialized"
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
    
    # Register new image generation preferences
    bpy.utils.register_class(FALImageGenPreferences)
    bpy.types.Scene.fal_image_gen = bpy.props.PointerProperty(type=FALImageGenPreferences)
    
    # Register classes
    classes = (
        FALAddonPreferences,
        FAL_PT_MainPanel,
        FAL_OT_GenerateImage,
        FALImageGenPreferences
    )
    
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
            log_debug(f"Successfully registered class: {cls.__name__}")
        except Exception as e:
            log_error(f"Failed to register class {cls.__name__}: {str(e)}")
    
    log_info("FAL AI Image to 3D addon registration complete")


def unregister():
    """Unregister the addon and all its classes"""
    log_debug("Unregistering FAL AI Image to 3D addon")
    
    # Unregister classes in reverse order
    classes = (
        FAL_OT_GenerateImage,
        FAL_PT_MainPanel,
        FALAddonPreferences,
        FALImageGenPreferences
    )
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
            log_debug(f"Successfully unregistered class: {cls.__name__}")
        except Exception as e:
            log_error(f"Failed to unregister class {cls.__name__}: {str(e)}")
    
    # Unregister properties
    try:
        del bpy.types.Scene.fal_api_key_input
        del bpy.types.Scene.fal_install_log
        del bpy.types.Scene.fal_debug_log
        del bpy.types.Scene.fal_install_success
        del bpy.types.Scene.fal_install_in_progress
        del bpy.types.Scene.fal_install_progress
        del bpy.types.Scene.fal_install_pid
        del bpy.types.Scene.fal_image_gen
        del bpy.types.Scene.fal_status_message
        log_debug("Successfully unregistered properties")
    except Exception as e:
        log_error(f"Failed to unregister properties: {str(e)}")
    
    log_info("FAL AI Image to 3D addon unregistration complete")


# Only register if running as an addon
if __name__ == "__main__":
    try:
        register()
    except Exception as e:
        print(f"Error registering FAL AI Image to 3D addon: {str(e)}")