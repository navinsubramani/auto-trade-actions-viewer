# Build the Docker Image
# Use the --no-cache option to ensure that the image is built from scratch without using any cached layers.
# This is useful when you want to ensure that all changes are included in the build.
# This command builds the Docker image with the tag `bts_aialgo_viewer`
sudo docker build --no-cache -t bts_aialgo_viewer .

# Delete the previous built image if it exists
# Remove all stopped containers and dangling images
sudo docker rm $(sudo docker ps -a -q)
# Remove the image by its ID
sudo docker rmi <id>


# Run the Image as Container
sudo docker run -p 8501:8501 -v /home/navin/workspace/mytrade/auto-trade-actions-viewer/.data:/container_data bts_aialgo_viewer