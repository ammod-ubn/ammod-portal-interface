FROM nvidia/cuda:10.0-cudnn7-devel

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
	python3-opencv ca-certificates python3-dev python3-pip git curl wget sudo zip unzip  \
	cmake ninja-build && \
  rm -rf /var/lib/apt/lists/*
RUN ln -sv /usr/bin/python3 /usr/bin/python
RUN ln -sv /usr/bin/pip3 /usr/bin/pip

# install dependencies
# See https://pytorch.org/ for other options if you use a different version of CUDA
RUN pip install tensorboard cmake   # cmake from apt-get is too old
RUN pip install torch==1.2 torchvision==0.4 -f https://download.pytorch.org/whl/cu100/torch_stable.html

# set FORCE_CUDA because during `docker build` cuda is not accessible
ENV FORCE_CUDA="1"
# This will by default build detectron2 for all common cuda architectures and take a lot more time,
# because inside `docker build`, there is no way to tell which architecture will be used.
ARG TORCH_CUDA_ARCH_LIST="Kepler;Kepler+Tesla;Maxwell;Maxwell+Tegra;Pascal;Volta;Turing"
ENV TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}"

RUN pip install --upgrade pip

# custom dependencies
RUN pip install opencv-python matplotlib requests pytz pyrealsense2 tqdm av scikit-image pyyaml tensorboardX

COPY realsense-camera-trap /opt/realsense-camera-trap
WORKDIR /opt/realsense-camera-trap
RUN (cd aanet/nets/deform_conv && bash build.sh)