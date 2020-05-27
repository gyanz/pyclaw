#!/usr/bin/python

# Author: Xinsheng (Shawn) Qin
# date: 03/2016
# Modified by Katy Barnhart
# date 05/2020

from .vtkOverlappingAMR import vtkOverlappingAMR, vtkAMRBlock, vtkAMRBox
from .claw_find_overlapped import set_overlapped_status
import sys
import os
import numpy as np


def write(
    solution,
    frame,
    path="_output",
    file_prefix='claw',
    ):
    """Convert solution to VTK.

    For each input frame a folder input_prefixXXXX.vthb and a folder called
    input_prefixXXXX containing multiple files called
    input_prefixXXXX_<level>_<patch>.vti. Each of these

    To open in paraview, choose the group of vthb files, not the group of
    folders.

    Might need to do CellDataToPointData in paraview to use filters like WarpByScalar.

    Args:
        sol (int): frame number of the clawpack output file
        path (string): path for vtk output. Default: "_output".
        file_prefix (str): File name of output VTK files in input_path. Default
            is "claw".

    TODO ADD WRITE AUX OPTIONS.

    Examples
    --------
    >>> from clawpack.pyclaw import Solution
    >>> from clawpack.pyclaw.fileio.vtk import write as write_vtk
    >>> for frame in range(21):
    ...     path = "_output"
    ...     sol = Solution(frame, path=path, file_format="ascii")
    ...     write_vtk(sol, frame=frame)

    """
    assert(isinstance(frame, int))
    set_overlapped_status(solution)

    global_origin = solution.state.patch.lower_global  # base patch
    global_origin.append(0.0)  # append z
    global_origin = np.array(global_origin)
    levels = [state.patch.level-1 for state in solution.states]

    # shift base level to 0, since the base level in clawpack
    # is 1 while the base level in VTK is 0
    level_count = {}
    level_spacing = {}  # spacing of each level
    for i, level in enumerate(levels):
        if level in level_count.keys():
            level_count[level] = level_count[level] + 1
        else:
            level_count[level] = 1
            spacing = solution.states[i].patch.delta
            spacing.append(spacing[0])  # dz = dx
            spacing = np.array(spacing)
            level_spacing[level] = spacing
    num_levels = len(level_count.keys())

    # a list of num of patches at each level
    box_per_level = [item[1] for item in
                     sorted(level_count.items(),
                            key=lambda a: a[0])]
    box_per_level = np.array(box_per_level)
    AMRdata = vtkOverlappingAMR(global_origin, num_levels, box_per_level)

    states_sorted = sorted(solution.states, key=lambda a: a.patch.level)
    global_index = 0
#################################################
    for level in level_count.keys():
        nbox = level_count[level]
        block = vtkAMRBlock(level, nbox, level_spacing[level], global_origin)

        for index in range(box_per_level[level]):
            # ----each vtkAMRBlock can have multiple vtkAMRBox
            local_index = global_index + index
            origin = states_sorted[local_index].patch.lower_global
            origin.append(0.0)  # append z
            origin = np.array(origin)
            ndim = states_sorted[local_index].patch.num_cells_global
            ndim.append(0.0)  # mz
            ndim = np.array(ndim, dtype=np.int)
            ndim = ndim + 1  # ndim should be num of nodes
            amrbox = vtkAMRBox(origin, ndim)

            q = states_sorted[local_index].q
            for i in range(q.shape[0]-1):
                q_i = q[i, ...]
                q_i = q_i.transpose()
                amrbox.set_cell_data(q_i, "q_"+str(i))

            # this is where writing out aux files wouild happen.
            
            q_ol = q[-1, ...]  # last piece is used to mark overlapped cells
            q_ol = q_ol.transpose()
            amrbox.set_cell_data(q_ol, "vtkGhostType", "UInt8")

            # set vtkGhostType data
            # ghost_q = np.zeros(q[0, ...].shape, dtype=int)
            # ghost_q = ghost_q.transpose()
            # amrbox.set_cell_data(ghost_q, "vtkGhostType", data_type="UInt8")

            # shape = list(q1.shape)
            # shape.append(1)
            # point_data = np.ones( np.array(shape) + 1)
            # amrbox.set_point_data(point_data)
            block.attached_amrbox(amrbox)
            AMRdata.attached_block(level, block)

        global_index = global_index + box_per_level[level]

    filename = file_prefix+str(frame).zfill(4)
    AMRdata.write_ascii(path, filename)
