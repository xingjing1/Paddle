# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from trt_layer_auto_scan_test import TrtLayerAutoScanTest, SkipReasons
from program_config import TensorConfig, ProgramConfig
import numpy as np
import paddle.inference as paddle_infer
from functools import partial
from typing import Optional, List, Callable, Dict, Any, Set
import unittest


class TrtConvertMultiNMSTest(TrtLayerAutoScanTest):
    def is_program_valid(self, program_config: ProgramConfig) -> bool:
        return True

    def sample_program_configs(self):
        def generate_input1(attrs: List[Dict[str, Any]]):
            return np.random.random([1, 16128, 4]).astype(np.float32)

        def generate_input2(attrs: List[Dict[str, Any]]):
            return np.random.random([1, 12, 16128]).astype(np.float32)

        ## TODO try more params when TRT layer is implemented
        for background_label in [-1]:
            for score_threshold in [0.05]:
                for nms_top_k in [1000]:
                    for keep_top_k in [100]:
                        for nms_threshold in [0.3]:
                            for normalized in [False]:
                                dics = [{
                                    "background_label": background_label,
                                    "score_threshold": score_threshold,
                                    "nms_top_k": nms_top_k,
                                    "keep_top_k": keep_top_k,
                                    "nms_threshold": nms_threshold,
                                    "normalized": normalized
                                }]

                            ops_config = [{
                                "op_type": "multiclass_nms",
                                "op_inputs": {
                                    "BBoxes": ["bboxes_data"],
                                    "Scores": ["scores_data"]
                                },
                                "op_outputs": {
                                    "Out": ["multiclass_output_data"]
                                },
                                "op_attrs": dics[0]
                            }]
                            ops = self.generate_op_config(ops_config)

                            program_config = ProgramConfig(
                                ops=ops,
                                weights={},
                                inputs={
                                    "bboxes_data": TensorConfig(
                                        data_gen=partial(generate_input1,
                                                         dics)),
                                    "scores_data": TensorConfig(
                                        data_gen=partial(generate_input2, dics))
                                },
                                outputs=["multiclass_output_data"])

                            yield program_config

    def sample_predictor_configs(
            self, program_config) -> (paddle_infer.Config, List[int], float):
        def generate_dynamic_shape(attrs):
            self.dynamic_shape.min_input_shape = {"bboxes_data": [1, 16128, 4]}
            self.dynamic_shape.max_input_shape = {"bboxes_data": [4, 16128, 4]}
            self.dynamic_shape.opt_input_shape = {"bboxes_data": [1, 16128, 4]}
            self.dynamic_shape.min_input_shape = {
                "scores_data": [1, 100, 16128]
            }
            self.dynamic_shape.max_input_shape = {
                "scores_data": [4, 100, 16128]
            }
            self.dynamic_shape.opt_input_shape = {
                "scores_data": [1, 100, 16128]
            }

        def clear_dynamic_shape():
            self.dynamic_shape.min_input_shape = {}
            self.dynamic_shape.max_input_shape = {}
            self.dynamic_shape.opt_input_shape = {}

        def generate_trt_nodes_num(attrs, dynamic_shape):
            return 0, 4

        attrs = [
            program_config.ops[i].attrs
            for i in range(len(program_config.ops))
        ]

        # for static_shape
        clear_dynamic_shape()
        self.trt_param.precision = paddle_infer.PrecisionType.Float32
        yield self.create_inference_config(), generate_trt_nodes_num(
            attrs, False), 1e-5
        self.trt_param.precision = paddle_infer.PrecisionType.Half
        yield self.create_inference_config(), generate_trt_nodes_num(
            attrs, False), (1e-5, 1e-5)

        # for dynamic_shape
        generate_dynamic_shape(attrs)
        self.trt_param.precision = paddle_infer.PrecisionType.Float32
        yield self.create_inference_config(), generate_trt_nodes_num(attrs,
                                                                     True), 1e-5
        self.trt_param.precision = paddle_infer.PrecisionType.Half
        yield self.create_inference_config(), generate_trt_nodes_num(
            attrs, True), (1e-5, 1e-5)

    def test(self):
        self.run_test()


if __name__ == "__main__":
    unittest.main()
