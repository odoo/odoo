from ..utils.br_sped_writer import BrSpedWriter


class BrEfdContrib(BrSpedWriter):
    def build_blocks(self):
        bloco_0 = [
            self.write_line("0000", [self.company.name if self.company else "", self.period_from, self.period_to]),
            self.write_line("0110", ["1", "1"]),
        ]
        bloco_9 = [self.write_line("9999", [len(bloco_0) + 1])]
        self.write_block("0", bloco_0)
        self.write_block("9", bloco_9)
        return self.build_file()

