from dataclasses import dataclass

@dataclass
class Chunk:
    text:str
    file_path:str
    start_line:int
    end_line:int
    chunk_type:str

