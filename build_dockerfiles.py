import os
import glob
from utils import step_name_to_docker_name

def main():
    """
    A script for building the docker images for each process inside steps/
    """

    for step_dir in sorted(glob.glob(os.path.join(os.path.dirname(__file__), "steps", "*/"))):
        step_name = os.path.basename(os.path.normpath(step_dir))
        dockerfile = os.path.join(step_dir, "Dockerfile")
        
        # each step must have a Dockerfile
        assert os.path.exists(dockerfile)

        # build docker image
        if os.system(f'docker build -t "{step_name_to_docker_name(step_name)}" -f "{dockerfile}" "{step_dir}"') != 0:
            raise RuntimeError(f"failed to build step: {step_name}")


if __name__ == "__main__":
    main()