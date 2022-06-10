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

class Scope:
    def __init__(self, parent, name, inherit = None)    :
        self.parent = parent
        self.symbols = []
        self.name = name
        self.inherit = inherit
    def __str__(self):
        return ""

class Symbol:
    def __init__(self, name:str , typ:Type , value ,scope:Scope = None):
        self.name = name
        self.typ = typ
        self.value = value
        self.scope = scope

class CodeGenerator(Utils):
    def __init__(self):
        self.globalScope = Scope(None, "Global", None)
        predefine = [
            Symbol("Int", IntType(), None),
            Symbol("Float", FloatType(), None),
            Symbol("Boolean", BoolType(), None),
            Symbol("String", StringType(), None),
            Symbol("Void", VoidType(), None)
        ]
        self.globalScope.symbols += predefine
        ioPredefine = Scope(self.globalScope, "io", None)
        ioSymbol = Symbol("io", ClassType(Id("io")), None, ioPredefine)
        self.globalScope.symbols.append(ioSymbol)
        ios16ipados16 = [
            Symbol("readInt", MType([], IntType()), CName('io')),
            Symbol("readFloat", MType([], FloatType()), CName('io')),
            Symbol("readBool", MType([], BoolType()), CName('io')),
            Symbol("readStr", MType([], StringType()), CName('io')),
            Symbol("writeInt", MType([IntType()], VoidType()), CName('io')),
            Symbol("writeFloat", MType([FloatType()], VoidType()), CName('io')),
            Symbol("writeBool", MType([BoolType()], VoidType()), CName('io')),
            Symbol("writeStr", MType([StringType()], VoidType()), CName('io')),
        ]
        ioPredefine.symbols += ios16ipados16
        
    def gen(self, ast, dir_):
        gc = CodeGenVisitor(ast, self.globalScope, dir_)
        gc.visit(ast, None)

class ArrayPointerType(Type):
    def __init__(self, ctype):
        #cname: String
        self.eleType = ctype

    def __str__(self):
        return "ArrayPointerType({0})".format(str(self.eleType))

    def accept(self, v, param):
        return None
        
class SubBody():
    def __init__(self, frame, sym):
        #frame: Frame
        #sym: List[Symbol]

        self.frame = frame
        self.sym = sym

class Access():
    def __init__(self, frame, curscope, isLeft, isFirst: False):
        #frame: Frame
        #sym: List[Symbol]
        #isLeft: Boolean
        #isFirst: Boolean

        self.frame = frame
        self.curscope = curscope
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
        curScope = self.env
        for i in ast.decl:
            self.visit(i, curScope)
        self.emit.emitEPILOG()
        return c
    
    def visitIntLiteral(self, ast: IntLiteral, c: Access):
        return self.emit.emitPUSHICONST(str(ast.value), c.frame), IntType()
    def visitFloatLiteral(self, ast: FloatLiteral, c: Access):
        return self.emit.emitPUSHFCONST(str(ast.value), c.frame), FloatType()
    def visitStringLiteral(self, ast: StringLiteral, c: Access):
        return self.emit.emitPUSHCONST(ast.value, StringType(), c.frame), StringType()
    def visitBooleanLiteral(self, ast: BooleanLiteral, c: Access):
        return self.emit.emitPUSHICONST(str(ast.value).lower(), c.frame), BoolType()
    
    def visitBlock(self, ast: Block, c: SubBody):
        c.frame.enterScope(False)
        self.emit.checkFirst(self.emit.emitLABEL(c.frame.getStartLabel(), c.frame))

        scope = Scope(c.sym, "BlockScope")
        message = SubBody(c.frame, scope)
        for i in ast.inst:
            self.visit(i, message)
        self.emit.checkFirst(self.emit.emitLABEL(c.frame.getEndLabel(), c.frame))
        c.frame.exitScope()
    
    def visitClassDecl(self, ast: ClassDecl, c: Scope):
        parent = ""
        inherit_sym = None
        if ast.parentname is not None:
            parent= ast.parentname.name 
            inherit_sym = self.getSymbol(c, parent)
        self.emit.checkFirst(self.emit.emitPROLOG(ast.classname.name, parent))
        curScope = Scope(c, ast.classname.name, inherit_sym)
        c.symbols.append(Symbol(ast.classname.name, ClassType(Id(ast.classname.name)), None,  curScope))

        for i in ast.memlist:
            self.visit(i, curScope)
        return c
           
    def visitAttributeDecl(self, ast: AttributeDecl, c: Scope):
        attr, typ, isFinal, rhs = self.visit(ast.decl, c)
        c.symbols.append(Symbol(attr, typ, CName(c.name) ))
        if type(ast.kind) is Instance:
            self.emit.checkFirst(self.emit.emitATTRIBUTE(attr, typ, isFinal,  False))
            if rhs[0]:
                self.emit.checkFirst(rhs[0])
                self.emit.checkFirst(self.emit.emitPUTFIELD(attr, typ, None))    
        else:
            self.emit.checkFirst(self.emit.emitATTRIBUTE(attr, typ, isFinal,  True))
            if rhs[0]:
                self.emit.checkFirst(rhs[0])
                self.emit.checkFirst(self.emit.emitPUTSTATIC(attr, typ, None))
        return c
    
        
    def visitMethodDecl(self, ast: MethodDecl, c:Scope): 
        name = ast.name.name
        if name == "Constructor":
            name = "<init>"
        inTyp = []
        for i in ast.param:
            inTyp.append(self.visit(i[1], self.env))
        retTyp = self.getSymbol(c, "Void").typ
        for i in ast.body.inst:
            if type(i) is Return:
                if i.expr:
                    _, retTyp = self.visit(i.expr, Access(None, c, False, False)) ## Note
                break
        typ = MType(inTyp, retTyp)
        scope = Scope(c, name)
        methodSymbol = Symbol(name, typ, CName(c.name), scope)
        c.symbols.append(methodSymbol)
        message = SubBody(Frame(name, retTyp), scope )
        isStatic = True
        if type(ast.kind) is Instance:
            isStatic = False
            message.frame.getNewIndex()
        
        self.emit.checkFirst(self.emit.emitMETHOD(name, typ, isStatic, message.frame))
        message.frame.enterScope(True)
        for i in ast.param:
            paramName, paramTyp , isFinal, _ = self.visit(i, message)
            scope.symbols.append(Symbol(paramName, paramTyp, Index(message.frame.getCurrIndex())))
            self.emit.checkFirst(self.emit.emitVAR(message.frame.getCurrIndex(),paramName, paramTyp, message.frame.getStartLabel(), message.frame.getEndLabel(),isFinal, message.frame ))
            message.frame.getNewIndex()
        self.emit.checkFirst(self.emit.emitLABEL(message.frame.getStartLabel(), message.frame))
        for i in ast.body.inst:
            self.visit(i, message)
        self.emit.checkFirst(self.emit.emitLABEL(message.frame.getEndLabel(), message.frame))
        self.emit.checkFirst(self.emit.emitENDMETHOD(message.frame))
        message.frame.exitScope()
        return c

    def visitVarDecl(self, ast: VarDecl, c): 
        if type(c) is Scope: 
            name = ast.variable.name
            typ = self.visit(ast.type, Access(None, c, False, False))
            if ast.varInit is not None:
                varInit = self.visit(ast.varInit, Access(None, c, False, False))
            else:
                varInit = [None, None]
           
            return name, typ, False, varInit
        elif type(c) is Access:
            access = Access(c.frame, c.sym)
            name = ast.variable.name
            typ  = self.visit(ast.type, None)
            access.curscope.symbols.append(Symbol(name, typ, c.frame.getCurrIndex()))
            self.emit.checkFirst(self.emit.emitVAR(c.frame.getCurrIndex(),name, typ, c.frame.getStartLabel(), c.frame.getEndLabel(), False, c.frame))
            if ast.varInit is not None:
                varInit = self.visit(ast.varInit, access)
                self.emit.checkFirst(varInit[0])
                self.emit.checkFirst(self.emit.emitWRITEVAR(name, typ, c.frame.getCurrIndex(), c.frame))
            c.frame.getNewIndex()

    def visitConstDecl(self, ast: ConstDecl, c): 
        if type(c) is Scope:
            name = ast.constant.name
            typ = self.visit(ast.constType, Access(None, c, False, False))
            if ast.value is not None:
                varInit = self.visit(ast.value, c)
            else:
                varInit = [None, None]
           
            return name, typ, False, varInit
        elif type(c) is Access:
            access = Access(c.frame, c.sym)
            name = ast.constant.name
            typ  = self.visit(ast.constType, None)
            access.curscope.symbols.append(Symbol(name, typ, c.frame.getCurrIndex()))
            self.emit.checkFirst(self.emit.emitVAR(c.frame.getCurrIndex(), name, typ, c.frame.getStartLabel(), c.frame.getEndLabel(), False, c.frame))
            
            varInit = self.visit(ast.value, access)
            self.emit.checkFirst(varInit[0])
            self.emit.checkFirst(self.emit.emitWRITEVAR(name, typ, c.frame.getCurrIndex(), c.frame))
            c.frame.getNewIndex()
        
    def visitBinaryOp(self, ast: BinaryOp, o: Access):
        lCode, lType = self.visit(ast.left, o)
        rCode, rType = self.visit(ast.right, o)

        if ast.op in ['==', '!=', '<', '<=', '>', '>=']:
            return lCode + rCode + self.emit.emitREOP(ast.op, retType, o.frame), BoolType()
        elif ast.op in ['-', '+', '*', '/', '%']:        
            retType = FloatType() if FloatType in [type(x) for x in [lType, rType]] else IntType()
            if type(lType) is IntType and type(retType) == FloatType: lCode += self.emit.emitI2F(o.frame)
            if type(rType) is IntType and type(retType) == FloatType: rCode += self.emit.emitI2F(o.frame)
            if ast.op in ['+', '-']:
                return lCode + rCode + self.emit.emitADDOP(ast.op, retType, o.frame), retType
            if ast.op in ['*', '/']:
                return lCode + rCode + self.emit.emitMULOP(ast.op, retType, o.frame), retType
            if ast.op == '%':
                return lCode + rCode + self.emit.emitMOD(o.frame), retType
        elif ast.op == '||': 
            return lCode + rCode + self.emit.emitOROP(o.frame), retType
        elif ast.op == '&&': 
            return lCode + rCode + self.emit.emitANDOP(o.frame), retType

    def visitUnaryOp(self, ast: UnaryOp, o: Access):
        eleCode, eleType = self.visit(ast.body, o)
        if ast.op == '!': 
            return eleCode + self.emit.emitNOT(eleType, o.frame), eleType
        return eleCode + self.emit.emitNEGOP(eleType, o.frame), eleType

    def visitCallExpr(self, ast: CallExpr, c: Access): pass
    def visitCallStmt(self, ast: CallStmt, c: SubBody): pass
    def visitNewExpr(self, ast: NewExpr, c:Access): pass

    def visitNullLiteral(self, ast: NullLiteral, c): 
        return self.emit.emitPUSHNULL(c.frame)

    def visitSelfLiteral(self, ast: SelfLiteral, c:Access): 
        curScope = c.curscope
        while curScope.parent.parent is not None:
            curScope = curScope.parent
        Class_sym = self.getSymbol(curScope.parent, curScope.name )
        return self.emit.emitREADVAR(None,Class_sym.typ, 0 , c.frame ) , Class_sym.typ
    
    def visitId(self, ast: Id, o: Access):
        if o.frame is None:
            attr_sym = self.getSymbol(o.curscope, ast.name )
            if o.isLeft:
                return self.emit.emitPUTFIELD(o.curscope.name + "/" + ast.name, attr_sym.typ, o.frame), attr_sym.typ
            else:
                return self.emit.emitGETFIELD(o.curscope.name + "/" + ast.name, attr_sym.typ, o.frame), attr_sym.typ
        else:
            if type(o.isFirst) is bool and o.isFirst == False:
                attr_sym = self.getSymbol(o.curscope, ast.name )
                if o.isLeft:
                    return self.emit.emitPUTFIELD(o.curscope.name + "/" + ast.name, attr_sym.typ, o.frame), attr_sym.typ
                else:
                    return self.emit.emitGETFIELD(o.curscope.name + "/" + ast.name, attr_sym.typ, o.frame), attr_sym.typ
            else:
                var_sym = self.getSymbol(o.curscope, ast.name)
                if o.isLeft:
                    return self.emit.emitWRITEVAR(ast.name, var_sym.typ, var_sym.value.value, o.frame), var_sym.typ
                return self.emit.emitREADVAR(ast.name, var_sym.typ, var_sym.value.value, o.frame), var_sym.typ

    def visitFieldAccess(self, ast: FieldAccess, c:Access): 
        obj_code = ""
        classscope = self.getSymbol(self.env, ast.obj.name).scope
        
        field_code, field_typ = self.visit(ast.fieldname, Access(c.frame, classscope, c.isLeft, False))
        return obj_code + field_code, field_typ
    
    def visitIf(self, ast: If, o: SubBody): pass
    def visitFor(self, ast: For, o: SubBody): pass
    def visitBreak(self, ast: Break, o: SubBody): pass
    def visitContinue(self, ast: Continue, o: SubBody): pass

    def visitAssign(self, ast: Assign, o: SubBody):
        exprCode, expType = self.visit(ast.exp, Access(o.frame, o.sym, False, True))
        lhsCode, lhsType = self.visit(ast.lhs, Access(o.frame, o.sym, True, True))

        if type(lhsType) is FloatType and type(expType) is IntType: # Coerce int -> float
            exprCode = exprCode + self.emit.emitI2F(o.frame)
        stmt_code = exprCode + lhsCode
        self.emit.checkFirst(stmt_code)
        
    def visitReturn(self, ast: Return, o: SubBody):
        if ast.expr:
            exprCode, exprType = self.visit(ast.expr, Access(o.frame, o.sym, False, True))
            self.emit.checkFirst(exprCode)
        else: exprType = VoidType()
        self.emit.checkFirst(self.emit.emitRETURN(exprType, o.frame))
         
    def visitIntType(self, ast, c):
        return self.getSymbol(self.env, "Int")

    def visitFloatType(self, ast, c): 
        return  self.getSymbol(self.env, "Float" )

    def visitBoolType(self, ast, c): 
        return self.getSymbol(self.env, "Boolean" )

    def visitStringType(self, ast, c): 
        return self.getSymbol(self.env, "String")
    def visitClassType(self, ast, c): 
        return ast
    def visitVoidType(self, ast, c): 
        return self.getSymbol(self.env, "Void")
    
    def getSymbol(self, scope: Scope, name: str):
        cur = scope
        while(cur):
            for sym in cur.symbols:
                if sym.name == name:
                    return sym
            cur = cur.parent
    
