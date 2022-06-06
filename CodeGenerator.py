'''
 *   @author Nguyen Hua Phung
 *   @version 1.0
 *   23/10/2015
 *   This file provides a simple version of code generator
 *
'''
from Utils import *
from StaticCheck import *
from StaticError import *
from Emitter import Emitter
from Frame import Frame
from abc import ABC, abstractmethod

class Symbol: pass
class Scope: pass
class ScopedSymbol(Symbol, Scope): pass
class ClassSymbol(ScopedSymbol, Type): pass

# Static attribute and instance
# Refer to thing in class
class AttributeSymbol(Symbol):
    def __init__(self, name: str, type: Type, kind: SIKind, cv: Kind) -> None:
        self.name = name
        self.type = type        # IntType, FloatType
        self.kind = kind        # Static or Instance
        self.cv = cv            # Constant or variable

    def __str__(self) -> str:
        return "AttributeSymbol(" + str(self.name) + "," + str(self.type) + "," + str(self.kind) + "," + str(self.cv)+ ")"

# Refer to thing in method
class VariableSymbol(Symbol):
    def __init__(self, name: str, type: Type, cv: Kind) -> None:
        self.name = name
        self.type = type        # IntType, FloatType ...
        self.cv = cv          # Constant or variable or parameter

    def __str__(self) -> str:
        return "VariableSymbol(" + str(self.name) + "," + str(self.type) + "," + str(self.cv) + ")"

# IntType, Float, String, Boolean, Array and Class type
# are written in AST
class MethodSymbol(ScopedSymbol):
    def __init__(self, name: str, kind: SIKind, blockScope: Scope=None) -> None:
        self.name = name
        self.kind = kind
        self.symbols = []               # Store only the parameters
        self.blockScope = blockScope    # Use storing statement scope //// LATE INIT
        self.upperScope = None          # TODO: this use self. Look back the symbol in class Scope to find attribute
        self.insideClass = ""
        self.type = VoidType()

    def addSymbol(self, symbol: Symbol):
        self.symbols.append(symbol)

    def belongToClass(self, name: str):
        self.insideClass = name

    def trigger(self):
        self.blockScope.upperScope = self

    def typeInfer(self, type: Type):
        self.type = type

    def __str__(self) -> str:
        return "MethodSymbol(" + str(self.name) + "," + str(self.kind) + "," + str(len(self.symbols)) + ")"

class ClassSymbol(ScopedSymbol, Type):
    def __init__(self, name: str, type: Type, superClass: ClassSymbol=None) -> None:
        self.name = name
        self.type = type
        self.symbols = []
        self.superClass = superClass

    def allSymbols(self):
        super = self.superClass
        sym = self.symbols
        while super is not None:
            names = [i.name for i in sym]
            for i in super.symbols:
                # Dont need the previous declaration
                if i.name not in names:
                    sym.append(i)
            super = super.superClass
        return sym

    def __str__(self) -> str:
        return "ClassSymbol(" + str(self.name) + "," + str(self.type) + "," + str(len(self.symbols)) + "," + (self.superClass.name if self.superClass else "") + ")"

class GlobalScope(Scope):
    def __init__(self) -> None:
        self.symbols = []

    def __str__(self) -> str:
        return "GlobalScope(Global," + ','.join(str(i.name) for i in self.symbols) + ")"

class BlockScope(Scope):
    def __init__(self) -> None:
        self.symbols = []               # Store variable declaration in this scope Ex: For scope
        self.blockScope = []            # Reference if block scope have if statement or for statement
        self.upperScope = None          # Referenec to upperScope

    def addBlock(self, block: Scope):
        self.blockScope.append(block)

    def getToMethod(self):
        upper = self
        while upper.upperScope is not None:
            upper = upper.upperScope
        return upper

    def lookUpperPlease(self) -> List[Symbol]:
        sym = self.symbols
        upper = self.upperScope
        while upper is not None:
            names = [i.name for i in sym]
            for i in upper.symbols:
                # Dont need the previous declaration cause messing with type
                if i.name not in names:
                    sym.append(i)
            upper = upper.upperScope
        return sym

    def trigger(self) -> None:
        if self.blockScope != []:
            for i in self.blockScope:
                i.upperScope = self

    def lookClass(self):
        upper = self.upperScope
        while upper.upperScope is not None:
            upper = upper.upperScope
        return upper.insideClass


    def __str__(self) -> str:
        return "BlockScope(Block," + ','.join(str(i.name) for i in self.symbols) + (",Upper" if self.upperScope else "") + ")"

class CodeGenerator(Utils):
    def __init__(self):
        self.gl = GlobalScope()

    def gen(self, ast, dir_):
        #ast: AST
        #dir_: String
        gc = CodeGenVisitor(ast, self.gl, dir_)
        gc.visit(ast, None)

class StringType(Type):   
    def __str__(self):
        return "StringType"

    def accept(self, v, param):
        return None
class ArrayPointerType(Type):
    def __init__(self, ctype):
        #cname: String
        self.eleType = ctype

    def __str__(self):
        return "ArrayPointerType({0})".format(str(self.eleType))

    def accept(self, v, param):
        return None
class ClassType(Type):
    def __init__(self,cname):
        self.cname = cname
    def __str__(self):
        return "Class({0})".format(str(self.cname))
    def accept(self, v, param):
        return None
        
class SubBody():
    def __init__(self, frame, sym):
        #frame: Frame
        #sym: List[Symbol]

        self.frame = frame
        self.sym = sym

class Access():
    def __init__(self, frame, sym, isLeft, isFirst):
        #frame: Frame
        #sym: List[Symbol]
        #isLeft: Boolean
        #isFirst: Boolean

        self.frame = frame
        self.sym = sym
        self.isLeft = isLeft
        self.isFirst = isFirst

class Val(ABC):
    pass

class Index(Val):
    def __init__(self, value):
        #value: Int

        self.value = value

class CName(Val):
    def __init__(self, value):
        #value: String

        self.value = value

class CodeGenVisitor(BaseVisitor, Utils):
    def __init__(self, astTree, env, dir_):
        #astTree: AST
        #env: List[Symbol]
        #dir_: File

        self.astTree = astTree
        self.env = env
        self.className = "D96Class"
        self.path = dir_
        self.emit = Emitter(self.path + "/" + self.className + ".j")

    def visitProgram(self, ast: Program, c):
        #ast: Program
        #c: Any
        for i in ast.decl:
            self.visit(i, self.env)
        # generate default constructor
        # self.genMETHOD(FuncDecl(Id("<init>"), list(), None, Block(list(), list())), c, Frame("<init>", VoidType))
        return c
    
    def visitClassDecl(self, ast: ClassDecl, c):
        if ast.classname.name == "Program":
            self.emit.printout(self.emit.emitPROLOG(self.className, ""))
        else:
            parent = ""
            if ast.parentname is not None:
                parent = ast.parentname
            self.emit.printout(self.emit.emitPROLOG(ast.classname, parent))
        

        self.emit.emitEPILOG()
    
    def visitAttributeDecl(self, ast: AttributeDecl, c): pass
    def visitMethodDecl(self, ast: MethodDecl, c): pass
    def visitVarDecl(self, ast: VarDecl, c): pass
    def visitConstDecl(self, ast: ConstDecl, c): pass
    def visitBlock(self, ast: Block, c): pass
    def visitBinaryOp(self, ast: BinaryOp, c): pass
    def visitUnaryOp(self, ast: UnaryOp, c: Access):
        exprCode, exprType = self.visit(ast.body, c)
        if ast.op == '-': 
            return exprCode + self.emit.emitNEGOP(exprType, c.frame), exprType
        else:
            return exprCode + self.emit.emitNOT(exprType, c.frame), exprType
    def visitCallExpr(self, ast: CallExpr, c): pass
    def visitCallStmt(self, ast: CallStmt, c): pass
    def visitNewExpr(self, ast: NewExpr, c): pass
    def visitArrayLiteral(self, ast: ArrayLiteral, c): pass
    def visitNullLiteral(self, ast: NullLiteral, c): pass
    def visitSelfLiteral(self, ast: SelfLiteral, c): pass
    def visitAssign(self, ast: Assign, c): pass
    def visitId(self, ast: Id, c): pass
    def visitArrayCell(self, ast: ArrayCell, c): pass
    def visitFieldAccess(self, ast: FieldAccess, c): pass
    def visitFor(self, ast: For, c): pass
    def visitIf(self, ast: If, c): pass
    def visitBreak(self, ast: Break, c): pass
    def visitContinue(self, ast: Continue, c): pass
    def visitReturn(self, ast: Return, c): pass

    def visitIntLiteral(self, ast: IntLiteral, c: Access):
        return self.emit.emitPUSHICONST(str(ast.value), c.frame), IntType()
    def visitFloatLiteral(self, ast: FloatLiteral, c: Access):
        return self.emit.emitPUSHFCONST(str(ast.value), c.frame), FloatType()
    def visitStringLiteral(self, ast: StringLiteral, c: Access):
        frame = c.frame
        return self.emit.emitPUSHCONST(ast.value, StringType(), frame), StringType()
    def visitBooleanLiteral(self, ast: BooleanLiteral, c: Access):
        return self.emit.emitPUSHICONST(str(ast.value).lower(), c.frame), BoolType()


    def genMETHOD(self, consdecl, o, frame):
        #consdecl: FuncDecl
        #o: Any
        #frame: Frame

        isInit = consdecl.returnType is None
        isMain = consdecl.name.name == "main" and len(consdecl.param) == 0 and type(consdecl.returnType) is VoidType
        returnType = VoidType() if isInit else consdecl.returnType
        methodName = "<init>" if isInit else consdecl.name.name
        intype = [ArrayPointerType(StringType())] if isMain else list()
        mtype = MType(intype, returnType)

        self.emit.printout(self.emit.emitMETHOD(methodName, mtype, not isInit, frame))

        frame.enterScope(True)

        glenv = o

        # Generate code for parameter declarations
        if isInit:
            self.emit.printout(self.emit.emitVAR(frame.getNewIndex(), "this", ClassType(self.className), frame.getStartLabel(), frame.getEndLabel(), frame))
        if isMain:
            self.emit.printout(self.emit.emitVAR(frame.getNewIndex(), "args", ArrayPointerType(StringType()), frame.getStartLabel(), frame.getEndLabel(), frame))

        body = consdecl.body
        self.emit.printout(self.emit.emitLABEL(frame.getStartLabel(), frame))

        # Generate code for statements
        if isInit:
            self.emit.printout(self.emit.emitREADVAR("this", ClassType(self.className), 0, frame))
            self.emit.printout(self.emit.emitINVOKESPECIAL(frame))
        list(map(lambda x: self.visit(x, SubBody(frame, glenv)), body.stmt))

        self.emit.printout(self.emit.emitLABEL(frame.getEndLabel(), frame))
        if type(returnType) is VoidType:
            self.emit.printout(self.emit.emitRETURN(VoidType(), frame))
        self.emit.printout(self.emit.emitENDMETHOD(frame))
        frame.exitScope();

    def visitFuncDecl(self, ast, o):
        #ast: FuncDecl
        #o: Any

        subctxt = o
        frame = Frame(ast.name, ast.returnType)
        self.genMETHOD(ast, subctxt.sym, frame)
        return SubBody(None, [Symbol(ast.name, MType(list(), ast.returnType), CName(self.className))] + subctxt.sym)

    def visitCallExpr(self, ast, o):
        #ast: CallExpr
        #o: Any

        ctxt = o
        frame = ctxt.frame
        nenv = ctxt.sym
        sym = self.lookup(ast.method.name, nenv, lambda x: x.name)
        cname = sym.value.value
    
        ctype = sym.mtype

        in_ = ("", list())
        for x in ast.param:
            str1, typ1 = self.visit(x, Access(frame, nenv, False, True))
            in_ = (in_[0] + str1, in_[1].append(typ1))
        self.emit.printout(in_[0])
        self.emit.printout(self.emit.emitINVOKESTATIC(cname + "/" + ast.method.name, ctype, frame))

    def visitIntLiteral(self, ast, o):
        #ast: IntLiteral
        #o: Any

        ctxt = o
        frame = ctxt.frame
        return self.emit.emitPUSHICONST(ast.value, frame), IntType()

    
