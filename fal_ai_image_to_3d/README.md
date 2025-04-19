# FAL AI Image to 3D Blender Addon

This addon allows you to generate AI images using FAL AI and convert them to 3D meshes directly in Blender.

## Installation

1. Download the `fal_ai_image_to_3d` folder
2. In Blender, go to Edit > Preferences > Add-ons
3. Click "Install" and select the `fal_ai_image_to_3d` folder
4. Enable the addon by checking the box next to "FAL AI Image to 3D"

## Usage

1. Set up your FAL API key in the addon preferences (Edit > Preferences > Add-ons > FAL AI Image to 3D)
2. Open the FAL AI panel in the 3D Viewport sidebar (N-panel)
3. Configure your image generation settings:
   - Enter your prompt and negative prompt
   - Adjust image dimensions and inference steps
   - Set mesh processing parameters
4. Click "Generate Image and Convert to 3D"

## Features

- Generate AI images using FAL AI's API
- Convert generated images to 3D meshes
- Automatic mesh cleanup:
  - Merge vertices by distance
  - Set origin to bottom center
  - Move to ground plane
- Customizable image generation parameters
- Secure API key management

## Requirements

- Blender 3.0 or later
- Internet connection for FAL API access
- Valid FAL API key

## Support

For issues or questions, please open an issue in the repository.

## License

This project is licensed under the terms included in the LICENSE file. 