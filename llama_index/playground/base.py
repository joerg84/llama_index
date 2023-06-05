"""Experiment with different indices, models, and more."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Type, Union

import pandas as pd
from langchain.input import get_color_mapping, print_text

from llama_index.indices.base import BaseGPTIndex
from llama_index.indices.list.base import ListIndex, ListRetrieverMode
from llama_index.indices.tree.base import GPTTreeIndex, TreeRetrieverMode
from llama_index.indices.vector_store import GPTVectorStoreIndex
from llama_index.readers.schema.base import Document

DEFAULT_INDEX_CLASSES: List[Type[BaseGPTIndex]] = [
    GPTVectorStoreIndex,
    GPTTreeIndex,
    ListIndex,
]

INDEX_SPECIFIC_QUERY_MODES_TYPE = Dict[Type[BaseGPTIndex], List[str]]

DEFAULT_MODES: INDEX_SPECIFIC_QUERY_MODES_TYPE = {
    GPTTreeIndex: [e.value for e in TreeRetrieverMode],
    ListIndex: [e.value for e in ListRetrieverMode],
    GPTVectorStoreIndex: ["default"],
}


class Playground:
    """Experiment with indices, models, embeddings, retriever_modes, and more."""

    def __init__(
        self,
        indices: List[BaseGPTIndex],
        retriever_modes: INDEX_SPECIFIC_QUERY_MODES_TYPE = DEFAULT_MODES,
    ):
        """Initialize with indices to experiment with.

        Args:
            indices: A list of BaseGPTIndex's to experiment with
            retriever_modes: A list of retriever_modes that specify which nodes are
                chosen from the index when a query is made. A full list of
                retriever_modes available to each index can be found here:
                https://gpt-index.readthedocs.io/en/latest/reference/query.html
        """
        self._validate_indices(indices)
        self._indices = indices
        self._validate_modes(retriever_modes)
        self._retriever_modes = retriever_modes

        index_range = [str(i) for i in range(len(indices))]
        self.index_colors = get_color_mapping(index_range)

    @classmethod
    def from_docs(
        cls,
        documents: List[Document],
        index_classes: List[Type[BaseGPTIndex]] = DEFAULT_INDEX_CLASSES,
        retriever_modes: INDEX_SPECIFIC_QUERY_MODES_TYPE = DEFAULT_MODES,
        **kwargs: Any,
    ) -> Playground:
        """Initialize with Documents using the default list of indices.

        Args:
            documents: A List of Documents to experiment with.
        """
        if len(documents) == 0:
            raise ValueError(
                "Playground must be initialized with a nonempty list of Documents."
            )

        indices = [
            index_class.from_documents(documents, **kwargs)
            for index_class in index_classes
        ]
        return cls(indices, retriever_modes)

    def _validate_indices(self, indices: List[BaseGPTIndex]) -> None:
        """Validate a list of indices."""
        if len(indices) == 0:
            raise ValueError("Playground must have a non-empty list of indices.")
        for index in indices:
            if not isinstance(index, BaseGPTIndex):
                raise ValueError(
                    "Every index in Playground should be an instance of BaseGPTIndex."
                )

    @property
    def indices(self) -> List[BaseGPTIndex]:
        """Get Playground's indices."""
        return self._indices

    @indices.setter
    def indices(self, indices: List[BaseGPTIndex]) -> None:
        """Set Playground's indices."""
        self._validate_indices(indices)
        self._indices = indices

    def _validate_modes(self, retriever_modes: INDEX_SPECIFIC_QUERY_MODES_TYPE) -> None:
        """Validate a list of retriever_modes."""
        if len(retriever_modes) == 0:
            raise ValueError(
                "Playground must have a nonzero number of retriever_modes."
                "Initialize without the `retriever_modes` "
                "argument to use the default list."
            )

    @property
    def retriever_modes(self) -> dict:
        """Get Playground's indices."""
        return self._retriever_modes

    @retriever_modes.setter
    def retriever_modes(self, retriever_modes: INDEX_SPECIFIC_QUERY_MODES_TYPE) -> None:
        """Set Playground's indices."""
        self._validate_modes(retriever_modes)
        self._retriever_modes = retriever_modes

    def compare(
        self, query_text: str, to_pandas: Optional[bool] = True
    ) -> Union[pd.DataFrame, List[Dict[str, Any]]]:
        """Compare index outputs on an input query.

        Args:
            query_text (str): Query to run all indices on.
            to_pandas (Optional[bool]): Return results in a pandas dataframe.
                True by default.

        Returns:
            The output of each index along with other data, such as the time it took to
            compute. Results are stored in a Pandas Dataframe or a list of Dicts.
        """
        print(f"\033[1mQuery:\033[0m\n{query_text}\n")
        result = []
        for i, index in enumerate(self._indices):
            for retriever_mode in self._retriever_modes[type(index)]:
                start_time = time.time()

                index_name = type(index).__name__
                print_text(
                    f"\033[1m{index_name}\033[0m, retriever mode = {retriever_mode}",
                    end="\n",
                )
                # TODO: refactor query mode
                try:
                    query_engine = index.as_query_engine(retriever_mode=retriever_mode)
                except ValueError:
                    continue

                output = query_engine.query(query_text)
                print_text(str(output), color=self.index_colors[str(i)], end="\n\n")

                duration = time.time() - start_time

                llm_token_usage = index.service_context.llm_predictor.last_token_usage
                embed_token_usage = index.service_context.embed_model.last_token_usage

                result.append(
                    {
                        "Index": index_name,
                        "Retriever Mode": retriever_mode,
                        "Output": str(output),
                        "Duration": duration,
                        "LLM Tokens": llm_token_usage,
                        "Embedding Tokens": embed_token_usage,
                    }
                )
        print(f"\nRan {len(result)} combinations in total.")

        if to_pandas:
            return pd.DataFrame(result)
        else:
            return result
